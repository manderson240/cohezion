import sys

import dbus


def set_resolution(width, height):
    bus = dbus.SessionBus()
    proxy = bus.get_object("org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig")
    iface = dbus.Interface(proxy, dbus_interface="org.gnome.Mutter.DisplayConfig")

    # GetCurrentState OUT u serial, a((ssss)a(siiddada{sv})a{sv}) monitors, a(iiduba(ssss)a{sv}) logical_monitors, a{sv} properties
    res = iface.GetCurrentState()
    serial = res[0]
    monitors_data = res[1]
    logical_monitors = res[2]

    # Map connector to available modes
    connector_to_modes = {}
    for monitor in monitors_data:
        # monitor[0] is (connector, vendor, product, serial)
        connector = monitor[0][0]
        # monitor[1] is a list of modes (id, w, h, refresh, scale, ...)
        modes = monitor[1]
        connector_to_modes[connector] = modes

    new_logical_monitors = []
    for lm in logical_monitors:
        x, y, scale, transform, primary, monitors_list, _properties = lm

        # monitors_list in logical_monitors is a list of (connector, vendor, product, serial)
        connector = monitors_list[0][0]

        if primary:
            # Find best mode_id for this connector that matches width/height
            available_modes = connector_to_modes.get(connector, [])
            best_mode_id = None
            for mode in available_modes:
                # mode is (id, w, h, refresh, ...)
                m_id, m_w, m_h = mode[0], mode[1], mode[2]
                if int(m_w) == int(width) and int(m_h) == int(height):
                    best_mode_id = m_id
                    break

            if not best_mode_id:
                print(f"❌ Error: Resolution {width}x{height} not supported by monitor {connector}")
                sys.exit(1)

            new_logical_monitors.append(
                dbus.Struct(
                    (
                        int(x),
                        int(y),
                        float(scale),
                        int(transform),
                        bool(primary),
                        [dbus.Struct((connector, best_mode_id, {}), signature="ssa{sv}")],
                    ),
                    signature="iiduba(ssa{sv})",
                )
            )
        else:
            # For non-primary monitors, just keep existing mode (need to find its ID)
            # This is complex, but on Framework there's usually only one monitor.
            # We'll just skip other monitors for now if any.
            pass

    iface.ApplyMonitorsConfig(serial, 2, new_logical_monitors, {})
    print(f"✅ Resolution set to {width}x{height}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        pass
    else:
        set_resolution(int(sys.argv[1]), int(sys.argv[2]))
