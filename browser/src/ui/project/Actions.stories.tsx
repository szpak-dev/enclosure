import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { SirenResponseError } from "../../client/SirenClient";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  SirenActionExecutionProvider,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import { ProjectActions, type ProjectActionsProps } from "./ProjectActions";

const bindingAction = sirenFixtures.action(
  "get_project_operating_contract_binding",
  "Read operating contract binding",
  "/siren/projects/project-1/operating-contract-binding",
  "GET",
  [],
);
const bindingActionTitle = "Read operating contract binding";
const conflict = sirenFixtures.entity(
  ["command-result"],
  "Operating contract is not configured",
  {
    detail: "Select an operating contract and expected revision.",
    project_id: "project-1",
    status: "conflict",
  },
  [
    sirenFixtures.link(
      "/siren/operating-contracts",
      ["collection"],
      "OperatingContract",
    ),
  ],
  [],
  [],
);
const execute = fn<SirenActionExecutor>(async () => {
  throw new SirenResponseError(
    409,
    bindingAction.href.toString(),
    "Operating contract is not configured",
    "Operating contract is not configured",
    [],
    {},
    conflict,
  );
});

const meta = {
  component: ProjectActions,
  args: {
    actions: [bindingAction],
    dangerNames: [],
    omitNames: [],
    onRefresh: fn(),
    primaryName: bindingAction.name,
    values: {},
  },
  decorators: [
    (Story) => (
      <SirenActionExecutionProvider execute={execute}>
        <Story />
      </SirenActionExecutionProvider>
    ),
  ],
  title: "Browser/Projects/Actions",
} satisfies Meta<ProjectActionsProps>;

export default meta;
type Story = StoryObj<typeof meta>;

export const OperatingContractConflict: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: bindingActionTitle }),
    );
    const dialog = await page.findByRole("dialog", {
      name: bindingActionTitle,
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: bindingActionTitle }),
    );
    await expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "not configured",
    );
    await expect(
      within(dialog).queryByText("Action completed"),
    ).not.toBeInTheDocument();
    await expect(within(dialog).getByText("project-1")).toBeVisible();
  },
};
