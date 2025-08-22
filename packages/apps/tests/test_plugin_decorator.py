"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.apps.plugins import Plugin, PluginBase, PluginOptions, get_metadata


class TestPluginDecorator:
    def test_plugin_with_metadata(self):
        @Plugin(name="test", version="0.2.0", description="testing123")
        class Test(PluginBase):
            pass

        metadata = get_metadata(Test)

        assert metadata is not None
        assert isinstance(metadata, PluginOptions)
        assert metadata.name == "test"
        assert metadata.version == "0.2.0"
        assert metadata.description == "testing123"

    def test_plugin_with_default_metadata(self):
        """Test plugin decorator with default metadata"""

        @Plugin()
        class Test(PluginBase):
            pass

        metadata = get_metadata(Test)

        assert metadata is not None
        assert isinstance(metadata, PluginOptions)
        assert metadata.name == "Test"
        assert metadata.version == "0.0.0"
        assert metadata.description == ""
