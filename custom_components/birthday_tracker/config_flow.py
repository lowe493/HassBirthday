"""Select an existing Home Assistant calendar entity."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_CALENDAR

class BirthdayTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CALENDAR])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Birthdays ({user_input[CONF_CALENDAR]})", data=user_input)
        schema = vol.Schema({vol.Required(CONF_CALENDAR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="calendar"))})
        return self.async_show_form(step_id="user", data_schema=schema)
