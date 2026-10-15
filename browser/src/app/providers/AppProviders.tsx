import {
  createTheme,
  MantineProvider,
  type CSSVariablesResolver,
} from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

type AppProvidersProps = {
  children: ReactNode;
};

const theme = createTheme({ primaryShade: 8 });
const colors: CSSVariablesResolver = () => ({
  dark: {
    "--mantine-color-dimmed": "var(--mantine-color-gray-4)",
  },
  light: {
    "--mantine-color-dimmed": "var(--mantine-color-dark-3)",
  },
  variables: {},
});

export function AppProviders({ children }: AppProvidersProps): ReactNode {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <MantineProvider cssVariablesResolver={colors} theme={theme}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MantineProvider>
  );
}
