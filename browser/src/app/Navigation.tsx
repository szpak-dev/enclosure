import { AppShell, ScrollArea } from "@mantine/core";
import type { Target } from "@siren-js/client";
import { SirenNavigation } from "../ui/siren/SirenNavigation";
import type { NavigationGroup } from "../ui/siren/SirenNavigationModel";

export type NavigationProps = {
  groups: readonly NavigationGroup[];
  onFollow: (target: Target) => void;
  target: Target;
};

export function Navigation({ groups, onFollow, target }: NavigationProps) {
  return (
    <AppShell.Navbar p="md">
      <ScrollArea>
        <SirenNavigation
          activeTarget={target}
          groups={groups}
          onFollow={onFollow}
        />
      </ScrollArea>
    </AppShell.Navbar>
  );
}
