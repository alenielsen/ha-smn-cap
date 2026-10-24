"""Alert summary sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SEVERITY = {"Unknown": 0, "Minor": 1, "Moderate": 2, "Severe": 3, "Extreme": 4}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SMNCount(coordinator, entry), SMNLevel(coordinator, entry)])

class SMNBase(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "SMN Alertas CAP", "manufacturer": "SMN (datos) / Comunidad (integración)"}

    @property
    def _alerts(self):
        return self.coordinator.data["alerts"]

    @property
    def extra_state_attributes(self):
        return {"alerts": self._alerts[:30], "last_success": self.coordinator.data["checked_at"], "source": "SMN - CAP"}

class SMNCount(SMNBase):
    _attr_name = "Cantidad de alertas"
    _attr_icon = "mdi:weather-lightning"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_count"

    @property
    def native_value(self):
        return len(self._alerts)

class SMNLevel(SMNBase):
    _attr_name = "Severidad máxima"
    _attr_icon = "mdi:alert"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_severity"

    @property
    def native_value(self):
        if not self._alerts:
            return "Sin alertas"
        return max((a["severity"] for a in self._alerts), key=lambda x: SEVERITY.get(x, 0))
