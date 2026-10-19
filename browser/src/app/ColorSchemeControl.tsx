import {
  ActionIcon,
  Menu,
  Tooltip,
  useMantineColorScheme,
  type MantineColorScheme,
} from "@mantine/core";
import {
  IconCheck,
  IconDeviceDesktop,
  IconMoon,
  IconSun,
  type TablerIcon,
} from "@tabler/icons-react";

type ColorSchemeOption = {
  icon: TablerIcon;
  label: string;
};

const colorSchemeOrder: readonly MantineColorScheme[] = [
  "auto",
  "light",
  "dark",
];

const colorSchemeOptions: Record<MantineColorScheme, ColorSchemeOption> = {
  auto: { icon: IconDeviceDesktop, label: "System" },
  dark: { icon: IconMoon, label: "Dark" },
  light: { icon: IconSun, label: "Light" },
};

export function ColorSchemeControl() {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const selected = colorSchemeOptions[colorScheme];
  const SelectedIcon = selected.icon;
  const label = `Color scheme: ${selected.label}`;

  return (
    <Menu position="bottom-end" shadow="md" transitionProps={{ duration: 0 }}>
      <Menu.Target>
        <Tooltip label={label}>
          <ActionIcon aria-label={label} size="lg">
            <SelectedIcon aria-hidden size={18} />
          </ActionIcon>
        </Tooltip>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>Color scheme</Menu.Label>
        {colorSchemeOrder.map((scheme) => {
          const option = colorSchemeOptions[scheme];
          const OptionIcon = option.icon;
          const selectedOption = scheme === colorScheme;
          return (
            <Menu.Item
              aria-checked={selectedOption}
              key={scheme}
              leftSection={<OptionIcon aria-hidden size={16} />}
              onClick={() => setColorScheme(scheme)}
              rightSection={selectedOption ? <IconCheck size={16} /> : null}
              role="menuitemradio"
            >
              {option.label}
            </Menu.Item>
          );
        })}
      </Menu.Dropdown>
    </Menu>
  );
}
