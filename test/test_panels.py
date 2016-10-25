from nose.tools import assert_equals

class TestGPIOPanel():
    @classmethod
    def setup_class(cls):
        from program.gpio_panel import GPIOPanel
        cls.g = GPIOPanel()

    @classmethod
    def teardown_class(cls):
        pass

    def test_creation(self):
        assert_equals(self.g.pane_id, 'sensorscience.unimeas.gpio_pane')
