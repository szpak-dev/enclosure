import { AppShell, Burger, Group, Text } from "@mantine/core";

export type AppHeaderProps = {
  navigationOpened: boolean;
  onToggleNavigation: () => void;
};

export function AppHeader({
  navigationOpened,
  onToggleNavigation,
}: AppHeaderProps) {
  return (
    <AppShell.Header>
      <Group h="100%" justify="space-between" px="md">
        <Group>
          <Burger
            aria-label="Toggle navigation"
            hiddenFrom="sm"
            onClick={onToggleNavigation}
            opened={navigationOpened}
            size="sm"
          />
          <Text fw={700}>Enclosure</Text>
        </Group>
      </Group>
    </AppShell.Header>
  );
}
