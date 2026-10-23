"""Config flow."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

class SMNCAPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input['latitude']:.4f},{user_input['longitude']:.4f}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"SMN CAP - {user_input['location']}", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("location", default="Necochea"): cv.string,
            vol.Required("latitude", default=round(self.hass.config.latitude, 5)): vol.Coerce(float),
            vol.Required("longitude", default=round(self.hass.config.longitude, 5)): vol.Coerce(float),
        }))
