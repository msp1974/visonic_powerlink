# HA Integration for Visonic Powerlink

This is a HA integration designed to work with the Visonic Proxy HA Addon, which will need to be installed and running before using this integration.  Please see https://github.com/msp1974/visonic_proxy for how to do this.


## Installing

This will be installable via HACS in the near future, but for now, please clone the repository to your machine and copy the custom_components/visonic_powerlink folder to a visonic_powerlink folder in your config/custom_components directory of your HomeAssistant instance.

## Config

There are only 3 parameters to configure

- Host: The hostname or ip of your HA instance running the visonic proxy addon
- Port: Unless you have a conflict and have changed the port in the addon, this should be 8082
- Require pin to arm/disarm - this setting is your choice.  If set to not require a pin, the Visonic Proxy will use the pin of the Master User (ie user 1) to perform arm/disarm functions.

## Issues

Please log issues on the github repo, providing a diagnostics download (this is anonymised for any sensitive data) and a clear description of the issue.