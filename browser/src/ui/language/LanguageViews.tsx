import {
  ActionIcon,
  Alert,
  Anchor,
  Button,
  Group,
  List,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconArrowRight, IconRefresh } from "@tabler/icons-react";
import type { Entity, Target } from "@siren-js/client";
import { Component, type ReactNode } from "react";
import {
  Identity,
  ResourceCards,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import { SirenContinuation } from "../siren/SirenContinuation";
import type { SirenEntityProps } from "../siren/SirenEntity";
import {
  LanguageContract,
  type Language,
  type LanguageTarget,
} from "./LanguageContract";

class LanguageNavigation extends Component<{
  entity: Entity;
  root: Entity;
  onFollow: (target: Target) => void;
}> {
  private readonly contract = new LanguageContract();
  render(): ReactNode {
    const globalTargets = new Set(
      this.props.root.links.map((link) => this.contract.href(link)),
    );
    const links = this.props.entity.links.filter(
      (link) =>
        !link.rel.some((rel) =>
          ["self", "next", "previous", "prev"].includes(rel),
        ) && !globalTargets.has(this.contract.href(link)),
    );
    return links.length ? (
      <Section title="Related resources">
        <ResourceCards
          links={links}
          label={(link) => link.title || "Related resource"}
          onFollow={this.props.onFollow}
        />
      </Section>
    ) : (
      <></>
    );
  }
}

class LanguageReload extends Component<{
  target: LanguageTarget;
  onReload: () => void;
}> {
  render(): ReactNode {
    const target = this.props.target;
    return (
      <Group justify="flex-end">
        {target.kind === "available" ? (
          <Button
            variant="default"
            leftSection={<IconRefresh size={16} />}
            onClick={this.props.onReload}
          >
            Reload
          </Button>
        ) : (
          <Text c="dimmed" size="sm">
            Reload unavailable
          </Text>
        )}
      </Group>
    );
  }
}

class LanguageFailure extends Component<{
  reason: unknown;
  onRefresh: () => void;
}> {
  render(): ReactNode {
    return (
      <Alert title="Languages view unavailable" color="red" role="alert">
        <Stack>
          <Text>
            {this.props.reason instanceof Error
              ? this.props.reason.message
              : "Unable to read language metadata."}
          </Text>
          <Button onClick={this.props.onRefresh}>Reload</Button>
        </Stack>
      </Alert>
    );
  }
}

class LanguageExtensions extends Component<{ values: string[] }> {
  render(): ReactNode {
    return this.props.values.length ? (
      <Group gap="xs" aria-label="Source extensions">
        {this.props.values.map((value) => (
          <Text key={value} component="span" size="sm" ff="monospace">
            {value}
          </Text>
        ))}
      </Group>
    ) : (
      <Text c="dimmed" size="sm">
        No source extensions advertised
      </Text>
    );
  }
}

class LanguageRow extends Component<{
  language: Language;
  target: LanguageTarget;
  onFollow: (target: Target) => void;
}> {
  private readonly contract = new LanguageContract();
  render(): ReactNode {
    const { language, target, onFollow } = this.props;
    return (
      <List.Item px="md">
        <Group
          justify="space-between"
          wrap="nowrap"
          align="flex-start"
          w="100%"
        >
          <Stack gap="xs" miw={0}>
            <Stack gap={2}>
              {target.kind === "available" ? (
                <Anchor
                  fw={600}
                  href={`#${this.contract.href(target.target)}`}
                  onClick={(event) => {
                    event.preventDefault();
                    onFollow(target.target);
                  }}
                >
                  {language.name}
                </Anchor>
              ) : (
                <Text fw={600}>{language.name}</Text>
              )}
              <Text c="dimmed" size="sm">
                {language.id}
              </Text>
            </Stack>
            <LanguageExtensions values={language.extensions} />
            {language.aliases.length ? (
              <Text size="sm" c="dimmed">
                Aliases: {language.aliases.join(", ")}
              </Text>
            ) : (
              <></>
            )}
          </Stack>
          {target.kind === "available" ? (
            <Tooltip label={`Open ${language.name}`}>
              <ActionIcon
                component="a"
                variant="subtle"
                aria-label={`Open ${language.name}`}
                href={`#${this.contract.href(target.target)}`}
                onClick={(event) => {
                  event.preventDefault();
                  onFollow(target.target);
                }}
              >
                <IconArrowRight size={18} />
              </ActionIcon>
            </Tooltip>
          ) : (
            <Text size="sm" c="dimmed">
              Navigation unavailable
            </Text>
          )}
        </Group>
      </List.Item>
    );
  }
}

export class LanguageCollection extends Component<SirenEntityProps> {
  private readonly contract = new LanguageContract();
  render(): ReactNode {
    try {
      const rows = this.props.entity.entities.map((entity) => ({
        language: this.contract.read(entity),
        target: this.contract.target(entity),
      }));
      return (
        <ResourcePage
          title="Languages"
          description="Languages available for source processing and scaffolding."
        >
          <LanguageReload
            target={this.contract.target(this.props.entity)}
            onReload={this.props.onRefresh}
          />
          {rows.length ? (
            <List
              listStyleType="none"
              spacing="lg"
              styles={{
                itemWrapper: { width: "100%" },
                itemLabel: { width: "100%" },
              }}
            >
              {rows.map((row) => (
                <LanguageRow
                  key={row.language.id}
                  {...row}
                  onFollow={this.props.onFollow}
                />
              ))}
            </List>
          ) : (
            <Alert title="No languages available">
              The server has not advertised any supported languages.
            </Alert>
          )}
          <SirenContinuation
            entity={this.props.entity}
            onFollow={this.props.onFollow}
          />
          <LanguageNavigation
            entity={this.props.entity}
            root={this.props.root}
            onFollow={this.props.onFollow}
          />
        </ResourcePage>
      );
    } catch (reason) {
      return (
        <LanguageFailure reason={reason} onRefresh={this.props.onRefresh} />
      );
    }
  }
}

export class LanguageDetail extends Component<SirenEntityProps> {
  private readonly contract = new LanguageContract();
  render(): ReactNode {
    try {
      const language = this.contract.read(this.props.entity);
      return (
        <ResourcePage
          title={language.name}
          description="Language recognition metadata for source processing and scaffolding."
        >
          <LanguageReload
            target={this.contract.target(this.props.entity)}
            onReload={this.props.onRefresh}
          />
          <Identity label="Language ID" value={language.id} />
          <Section title="Recognized source extensions">
            <LanguageExtensions values={language.extensions} />
          </Section>
          <Section title="Aliases">
            {language.aliases.length ? (
              <Group gap="xs">
                {language.aliases.map((alias) => (
                  <Text key={alias} component="span" ff="monospace">
                    {alias}
                  </Text>
                ))}
              </Group>
            ) : (
              <Text c="dimmed">No aliases</Text>
            )}
          </Section>
          <LanguageNavigation
            entity={this.props.entity}
            root={this.props.root}
            onFollow={this.props.onFollow}
          />
        </ResourcePage>
      );
    } catch (reason) {
      return (
        <LanguageFailure reason={reason} onRefresh={this.props.onRefresh} />
      );
    }
  }
}
