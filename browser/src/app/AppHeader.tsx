import { AppShell, Group, Text } from "@mantine/core";

export function AppHeader() {
  return (
    <AppShell.Header>
      <Group h="100%" justify="space-between" px="md">
        <Text fw={700}>Enclosure</Text>
      </Group>
    </AppShell.Header>
  );
}
