"""Select a Home Assistant calendar and configure the birthday title keyword."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_CALENDAR, CONF_KEYWORD, DEFAULT_KEYWORD

class BirthdayTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CALENDAR])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Birthdays ({user_input[CONF_CALENDAR]})", data=user_input
            )
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_CALENDAR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar")
            ),
            vol.Optional(CONF_KEYWORD, default=DEFAULT_KEYWORD): str,
        }))

    @staticmethod
    def async_get_options_flow(config_entry):
        return BirthdayTrackerOptionsFlow(config_entry)

class BirthdayTrackerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            keyword = str(user_input.get(CONF_KEYWORD, DEFAULT_KEYWORD)).strip()
            if not keyword:
                return self.async_show_form(
                    step_id="init", data_schema=self._schema(),
                    errors={CONF_KEYWORD: "required"},
                )
            return self.async_create_entry(title="", data={CONF_KEYWORD: keyword})
        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        current = self._entry.options.get(
            CONF_KEYWORD, self._entry.data.get(CONF_KEYWORD, DEFAULT_KEYWORD)
        )
        return vol.Schema({vol.Required(CONF_KEYWORD, default=current): str})
