"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import random
from typing import Any, Dict

import aiohttp
from microsoft.teams.ai import Agent, Function
from microsoft.teams.ai.ai_model import AIModel
from microsoft.teams.api import MessageActivity, MessageActivityInput
from microsoft.teams.apps import ActivityContext
from pydantic import BaseModel


class SearchPokemonParams(BaseModel):
    pokemon_name: str
    """The name of the pokemon."""


class GetLocationParams(BaseModel):
    """No parameters needed for location"""

    pass


class GetWeatherParams(BaseModel):
    location: str
    """The location to get weather for"""


async def pokemon_search_handler(params: SearchPokemonParams) -> str:
    """Search for Pokemon using PokeAPI - matches documentation example"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pokeapi.co/api/v2/pokemon/{params.pokemon_name.lower()}") as response:
                if response.status != 200:
                    raise ValueError(f"Pokemon '{params.pokemon_name}' not found")

                data = await response.json()

                result_data = {
                    "name": data["name"],
                    "height": data["height"],
                    "weight": data["weight"],
                    "types": [type_info["type"]["name"] for type_info in data["types"]],
                }

                return f"Pokemon {result_data['name']}: height={result_data['height']}, weight={result_data['weight']}, types={', '.join(result_data['types'])}"  # noqa: E501
    except Exception as e:
        raise ValueError(f"Error searching for Pokemon: {str(e)}") from e


async def handle_pokemon_search(model: AIModel, ctx: ActivityContext[MessageActivity]) -> None:
    """Handle single function calling - Pokemon search"""
    agent = Agent(model)
    agent.with_function(
        Function(
            name="pokemon_search",
            description="Search for pokemon information including height, weight, and types",
            parameter_schema=SearchPokemonParams,
            handler=pokemon_search_handler,
        )
    )

    chat_result = await agent.send(
        input=ctx.activity.text, instructions="You are a helpful assistant that can look up Pokemon for the user."
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)
    else:
        await ctx.reply("Sorry I could not find that pokemon")


def get_location_handler(params: GetLocationParams) -> str:
    """Get user location (mock)"""
    locations = ["Seattle", "San Francisco", "New York"]
    location = random.choice(locations)
    return location


def get_weather_handler(params: BaseModel) -> str:
    """Get weather for location (mock)"""
    weather_by_location: Dict[str, Dict[str, Any]] = {
        "Seattle": {"temperature": 65, "condition": "sunny"},
        "San Francisco": {"temperature": 60, "condition": "foggy"},
        "New York": {"temperature": 75, "condition": "rainy"},
    }

    location = getattr(params, "location")  # noqa
    weather = weather_by_location.get(location)
    if not weather:
        return "Sorry, I could not find the weather for that location"

    return f"The weather in {location} is {weather['condition']} with a temperature of {weather['temperature']}°F"


async def handle_multiple_functions(model: AIModel, ctx: ActivityContext[MessageActivity]) -> None:
    """Handle multiple function calling - location then weather"""
    agent = Agent(model)

    agent.with_function(
        Function(
            name="get_user_location",
            description="Gets the location of the user",
            parameter_schema=GetLocationParams,
            handler=get_location_handler,
        )
    ).with_function(
        name="weather_search",
        description="Search for weather at a specific location",
        parameter_schema={
            "title": "GetWeatherParams",
            "type": "object",
            "properties": {"location": {"title": "Location", "type": "string"}},
            "required": ["location"],
        },
        handler=get_weather_handler,
    )

    chat_result = await agent.send(
        input=ctx.activity.text,
        instructions=(
            "You are a helpful assistant that can help the user get the weather."
            "First get their location, then get the weather for that location."
        ),
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)
    else:
        await ctx.reply("Sorry I could not figure it out")
