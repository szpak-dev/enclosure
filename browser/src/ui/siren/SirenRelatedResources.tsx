import { NavLink, Paper, Stack, Title } from "@mantine/core";
import type { Target } from "@siren-js/client";
import type { NavigationItem } from "./SirenNavigationModel";

export type SirenRelatedResourcesProps = {
  onFollow: (target: Target) => void;
  resources: readonly NavigationItem[];
};

export function SirenRelatedResources({
  onFollow,
  resources,
}: SirenRelatedResourcesProps) {
  if (!resources.length) return null;
  return (
    <Paper component="section" p="md" shadow="xs">
      <Stack gap="xs">
        <Title order={2}>Related resources</Title>
        {resources.map((resource) => (
          <NavLink
            component="a"
            href={`#${resource.target}`}
            key={resource.id}
            label={resource.label}
            onClick={(event) => {
              event.preventDefault();
              onFollow(resource.target);
            }}
          />
        ))}
      </Stack>
    </Paper>
  );
}
