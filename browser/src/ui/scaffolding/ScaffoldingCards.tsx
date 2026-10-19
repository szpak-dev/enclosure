import {
  Alert,
  Badge,
  Button,
  Card,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type { SubEntity, Target } from "@siren-js/client";
import { scaffoldingPresentation } from "./ScaffoldingPresentation";

export type ScaffoldingCardsProps = {
  items: readonly SubEntity[];
  onFollow: (target: Target) => void;
};

export function ScaffoldingCards({ items, onFollow }: ScaffoldingCardsProps) {
  if (!items.length)
    return (
      <Alert title="No scaffoldings found">
        No scaffolding matches this collection or search.
      </Alert>
    );
  return (
    <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }}>
      {items.map((item, index) => {
        const properties = scaffoldingPresentation.itemProperties(item);
        const id = scaffoldingPresentation.text(properties, "id");
        const target = scaffoldingPresentation.itemTarget(item);
        return (
          <Card key={`${id}-${index}`} padding="lg" radius="md" withBorder>
            <Stack justify="space-between" mih={220}>
              <Stack gap="xs">
                <Badge variant="light">
                  {scaffoldingPresentation.text(properties, "language_id")}
                </Badge>
                <Title order={3} size="h4">
                  {scaffoldingPresentation.text(properties, "name")}
                </Title>
                <Text c="dimmed" size="sm">
                  {scaffoldingPresentation.text(properties, "description")}
                </Text>
              </Stack>
              {target.kind === "present" ? (
                <Button
                  component="a"
                  href={`#${typeof target.target === "string" ? target.target : target.target.href}`}
                  onClick={(event) => {
                    event.preventDefault();
                    onFollow(target.target);
                  }}
                  variant="light"
                >
                  Open scaffolding
                </Button>
              ) : (
                <Text c="dimmed" size="sm">
                  This search result does not advertise a scaffolding
                  destination.
                </Text>
              )}
            </Stack>
          </Card>
        );
      })}
    </SimpleGrid>
  );
}
