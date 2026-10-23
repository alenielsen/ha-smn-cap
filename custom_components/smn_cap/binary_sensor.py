"""Alert presence."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SMNActive(hass.data[DOMAIN][entry.entry_id], entry)])

class SMNActive(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "Alerta meteorológica"
    _attr_icon = "mdi:weather-lightning"
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "SMN Alertas CAP"}

    @property
    def is_on(self):
        return bool(self.coordinator.data["alerts"])
