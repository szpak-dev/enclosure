import { Box, Code, SimpleGrid, Stack, Text } from "@mantine/core";
import type { Entity } from "@siren-js/client";
import { SirenValue, type SirenPropertyValue } from "./SirenValue";

const YAML_PROPERTIES = [
  ["shape_yaml", "Shape YAML"],
  ["boundaries_yaml", "Boundaries YAML"],
] as const;

export type SirenPropertiesProps = {
  entity: Entity;
  exclude?: string[];
};

export function SirenProperties({
  entity,
  exclude = [],
}: SirenPropertiesProps) {
  const entries = Object.entries(entity.properties).filter(
    (entry): entry is [string, SirenPropertyValue] =>
      !exclude.includes(entry[0]) &&
      entry[1] !== null &&
      entry[1] !== undefined,
  );
  const yamlNames = new Set<string>(YAML_PROPERTIES.map(([name]) => name));
  const properties = entries.filter(([name]) => !yamlNames.has(name));
  const yaml = new Map(entries);

  return (
    <Stack component="dl" gap="lg">
      {properties.length ? (
        <SimpleGrid cols={{ base: 1, sm: 2 }} component="div">
          {properties.map(([name, value]) => (
            <div key={name}>
              <Text component="dt" fw={600}>
                {name}
              </Text>
              <Box component="dd">
                <SirenValue value={value} />
              </Box>
            </div>
          ))}
        </SimpleGrid>
      ) : null}
      {YAML_PROPERTIES.flatMap(([name, label]) => {
        const value = yaml.get(name);
        return typeof value === "string"
          ? [
              <div key={name}>
                <Text component="dt" fw={600}>
                  {label}
                </Text>
                <Box component="dd" m={0}>
                  <Code
                    aria-label={`${label} configuration`}
                    block
                    style={{ maxHeight: "32rem", overflow: "auto" }}
                  >
                    {value}
                  </Code>
                </Box>
              </div>,
            ]
          : [];
      })}
    </Stack>
  );
}
