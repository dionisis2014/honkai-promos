# honkai-promos

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

This Docker container checks every 12 hours for new promo codes for Honkai Impact 3rd and triggers and event in Home
Assistant via MQTT.

![](https://static.wikia.nocookie.net/honkaiimpact3_gamepedia_en/images/6/64/Crystals.png/revision/latest/scale-to-width-down/128)
![](https://static.wikia.nocookie.net/honkaiimpact3_gamepedia_en/images/8/85/Houkai3rd_logo_JP.png)
![](https://static.wikia.nocookie.net/honkaiimpact3_gamepedia_en/images/6/64/Crystals.png/revision/latest/scale-to-width-down/128)

# Docker options

## Volume mounts

The container uses the `/mnt` directory to store its persistent data. Simply add `-v <volume_or_bind>:/mnt` to the
docker run command to persist changes across container restart or updates.

### Environment variables

| NAME          | DEFAULT             |       TYPE        | DESCRIPTION                                                      |
|---------------|---------------------|:-----------------:|------------------------------------------------------------------|
| `HASS_HOST`   | `homeassistant.lan` |  Hostname or IP   | The hostname or IP of the Home Assistant host                    |
| `HASS_USER`   | `user`              |      String       | The username to use for MQTT                                     |
| `HASS_PASS`   | `password`          |      String       | The password to use for MQTT                                     |
| `LOG_LEVEL`   | `INFO`              | String or Integer | The logging level. Uses Python logging library's levels          |
| `RETRY_DELAY` | `10`                |      Integer      | The delay in minutes between check attempts when something fails |

## Home Assistant

### Trigger

When new promo codes are found, a trigger event is sent to Home Assistant with an attached payload. The payload is a
JSON object defined by the below JSON Schema:

```json
{
  "type": "object",
  "properties": {
    "active": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "expired": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "active",
    "expired"
  ]
}
```

The `active` list contains all valid promo codes from the ones found and the `expired` list contains expired ones
respectively.

A sample payload may look like this:

```json
{
  "active": [
    "VERYPROMO",
    "MUCHCODE"
  ],
  "expired": [
    "SUCHSAD",
    "NOCRYSTALS"
  ]
}
```

## Home Assistant example

This example shows how to show a persistent notification in the Home Assistant frontend when new promo codes are found.
This uses a single automation for everything (including formatting).

### Steps

1. Create a new automation
2. In the `When` section, click `ADD TRIGGER` → `Device`
3. Select `Honkai Impact 3rd Promos` as the device
4. `"found_new" codes` should be auto selected as the trigger
5. In the `Then do` section, click `ADD ACTION` → `Notifications` → `Send a persistent notification`
6. Click the three dots in the block and select the `Edit in YAML` option
7. Set the `data: {}` line to the below snippet
8. Click the `SAVE` button in the bottom right corner and name the automation
9. Profit?

```yaml
data:
  message: >
    {% if trigger.payload_json['active'] -%}
      ## Active promo codes:

      {% for code in trigger.payload_json['active'] -%}
        - {{ code }}

      {% endfor -%}
      {% if trigger.payload_json['expired'] -%}
        ***

      {% endif -%}
    {% endif -%}
    {% if trigger.payload_json['expired'] -%}
      ## Expired promo codes:

      {% for code in trigger.payload_json['expired'] -%}
        - {{ code }}

      {% endfor -%}
    {% endif -%}
  title: New promo codes found
```

The above snippet does the following things:

- Shows a list with a header of active codes (if any)
- Add a separator between the two lists (if both are not empty)
- Shows a list with a header of expired codes (if any)
- Sets the notification title

## License

honkai-promos is available under the [GNU AGPLv3 ](https://www.gnu.org/licenses/agpl-3.0) license. See
the [LICENSE](/LICENSE) file for more information.

![](https://static.wikia.nocookie.net/honkaiimpact3_gamepedia_en/images/6/64/Crystals.png/revision/latest/scale-to-width-down/64)
![](https://static.wikia.nocookie.net/honkaiimpact3_gamepedia_en/images/9/9e/Yae_Sakura_-_Summer_Keychain.png)
![](https://static.wikia.nocookie.net/honkaiimpact3_gamepedia_en/images/6/64/Crystals.png/revision/latest/scale-to-width-down/64)

## Fight for All That is Beautiful in the World!
