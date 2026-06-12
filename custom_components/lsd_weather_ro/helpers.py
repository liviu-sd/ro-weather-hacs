from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from .const import DOMAIN


def get_device_info(
    domain: str, location_name: str, prefix: str = "anmh"
) -> DeviceInfo | None:
    # Standard device info for all sensors related to this location
    # device_info =

    manufacturer = "L.S.D."

    return DeviceInfo(
        identifiers={(domain, prefix + "_" + location_name)},
        name="ANMH " + location_name,
        manufacturer=manufacturer,
        model="Weather Station",
        entry_type=DeviceEntryType.SERVICE,  # "service",
    )


def get__attr_unique_id(domain: str, config_entry_id: str, suffix: str) -> str:
    return f"{DOMAIN}_{config_entry_id}_{suffix}"
