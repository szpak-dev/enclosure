import { Alert, AppShell, Button, Stack } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import type { Target } from "@siren-js/client";
import { useMemo, useState, type ReactElement } from "react";
import { SirenClient } from "../client/SirenClient";
import { navigationGroups } from "../ui/siren/SirenNavigationModel";
import { SirenPage } from "../ui/siren/SirenPage";
import { SirenActionExecutionProvider } from "../ui/siren/SirenActionExecution";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";
import { Navigation } from "./Navigation";
import { AppProviders } from "./providers/AppProviders";
import { useSirenBrowser } from "./useSirenBrowser";

export type AppProps = {
  rootTarget: string;
};

function Browser({ rootTarget }: AppProps): ReactElement {
  const [client] = useState(() => new SirenClient());
  const [
    navigationOpened,
    { close: closeNavigation, toggle: toggleNavigation },
  ] = useDisclosure();
  const state = useSirenBrowser(client, rootTarget);
  const groups = useMemo(
    () => navigationGroups(rootTarget, state.root?.links ?? []),
    [rootTarget, state.root],
  );
  const follow = (target: Target) => {
    state.follow(target);
    closeNavigation();
  };

  return (
    <AppShell
      footer={{ height: 48 }}
      header={{ height: 60 }}
      navbar={{
        breakpoint: "sm",
        collapsed: { mobile: !navigationOpened },
        width: 280,
      }}
      padding="md"
    >
      <AppHeader
        navigationOpened={navigationOpened}
        onToggleNavigation={toggleNavigation}
      />
      <Navigation groups={groups} onFollow={follow} target={state.target} />
      <AppShell.Main>
        <Stack>
          {state.rootError ? (
            <Alert color="red" role="alert" title="Navigation unavailable">
              <Stack gap="xs">
                {state.rootError.message}
                <Button onClick={state.retryRoot} size="xs" variant="light">
                  Retry navigation
                </Button>
              </Stack>
            </Alert>
          ) : null}
          {state.error ? (
            <Alert color="red" role="alert" title="Unable to load resource">
              <Stack gap="xs">
                {state.error.message}
                <Button onClick={state.retry} size="xs" variant="light">
                  Retry
                </Button>
              </Stack>
            </Alert>
          ) : (
            <SirenActionExecutionProvider execute={state.execute}>
              <SirenPage
                entity={state.entity}
                isLoading={state.isLoading}
                onFollow={follow}
                onLoad={state.load}
                onRefresh={state.retry}
                onSubmit={state.submit}
                root={state.root}
              />
            </SirenActionExecutionProvider>
          )}
        </Stack>
      </AppShell.Main>
      <AppFooter />
    </AppShell>
  );
}

export function App(props: AppProps): ReactElement {
  return (
    <AppProviders>
      <Browser {...props} />
    </AppProviders>
  );
}
