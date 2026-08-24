import { Alert, AppShell, Button, Stack } from "@mantine/core";
import { useState, type ReactElement } from "react";
import { SirenClient } from "../client/SirenClient";
import { SirenPage } from "../ui/siren/SirenPage";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";
import { AppProviders } from "./providers/AppProviders";
import { useSirenBrowser } from "./useSirenBrowser";

export type AppProps = {
  rootTarget: string;
};

function Browser({ rootTarget }: AppProps): ReactElement {
  const [client] = useState(() => new SirenClient());
  const state = useSirenBrowser(client, rootTarget);

  return (
    <AppShell footer={{ height: 48 }} header={{ height: 60 }} padding="md">
      <AppHeader
        links={state.root?.links ?? []}
        onFollow={state.follow}
        target={state.target}
      />
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
            <SirenPage
              entity={state.entity}
              isLoading={state.isLoading}
              onFollow={state.follow}
              onLoad={state.load}
              onRefresh={state.retry}
              onSubmit={state.submit}
              root={state.root}
            />
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
