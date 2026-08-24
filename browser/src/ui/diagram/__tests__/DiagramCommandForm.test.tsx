import { MantineProvider } from "@mantine/core";
import { Action, Field, type Entity, type Target } from "@siren-js/client";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SirenResponseError } from "../../../client/SirenClient";
import {
  JSON_CONTROL,
  STRUCTURED_FORM_EXTENSION,
} from "../../siren/SirenActionForm";
import { DiagramCommandForm } from "../DiagramCommandForm";

const commands = {
  add_example: {
    additionalProperties: false,
    properties: {
      id: { minLength: 1, title: "Id", type: "string" },
      label: { default: "", title: "Label", type: "string" },
    },
    required: ["id"],
    type: "object",
  },
  connect_examples: {
    additionalProperties: false,
    properties: {
      id: { minLength: 1, title: "Id", type: "string" },
      label: { default: "", title: "Label", type: "string" },
      source_id: { minLength: 1, title: "Source id", type: "string" },
      target_id: { minLength: 1, title: "Target id", type: "string" },
    },
    required: ["id", "source_id", "target_id"],
    type: "object",
  },
  configure_example: {
    additionalProperties: false,
    properties: {
      direction: {
        enum: ["forward", "backward"],
        title: "Direction",
        type: "string",
      },
      element_ids: {
        items: { type: "string" },
        title: "Element ids",
        type: "array",
      },
      metadata: {
        additionalProperties: false,
        properties: {
          note: { title: "Note", type: "string" },
        },
        title: "Metadata",
        type: "object",
      },
    },
    required: ["direction", "element_ids", "metadata"],
    type: "object",
  },
};

function field(name: string, type: string, title: string): Field {
  return Object.assign(new Field(), { name, title, type });
}

const action = Object.assign(new Action(), {
  fields: [
    field("expected_revision", "number", "Expected revision"),
    field("operation", "text", "Operation"),
  ],
  href: "/advertised-command-target",
  method: "POST",
  name: "execute_advertised_command",
  title: "Apply command",
  type: "application/json",
  [STRUCTURED_FORM_EXTENSION]: {
    controls: [
      {
        control: JSON_CONTROL,
        location: "body",
        mediaType: "application/json",
        name: "arguments",
        required: true,
        schema: { additionalProperties: {}, type: "object" },
      },
    ],
    version: "1",
  },
});

const root = {
  actions: [],
  class: ["api", "entry-point"],
  entities: [],
  links: [
    {
      href: "/advertised-catalogue",
      rel: ["collection"],
      title: "Advertised catalogue",
    },
  ],
  properties: {},
  title: "Example API",
} as unknown as Entity;

const catalogue = {
  actions: [],
  class: ["collection"],
  entities: [
    {
      class: ["item"],
      links: [
        {
          href: "/advertised-kind",
          rel: ["self"],
          title: "Advertised kind",
        },
      ],
      properties: { id: "example-kind" },
      rel: ["item"],
      title: "Example kind",
    },
  ],
  links: [],
  properties: {},
  title: "Advertised catalogue",
} as unknown as Entity;

const description = {
  actions: [],
  class: ["kind"],
  entities: [],
  links: [],
  properties: { commands },
  title: "Example kind",
} as unknown as Entity;

function href(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

function loader() {
  return vi.fn(async (target: Target) => {
    if (href(target) === "/advertised-catalogue") return catalogue;
    if (href(target) === "/advertised-kind") return description;
    throw new Error(`Unexpected target: ${href(target)}`);
  });
}

function renderForm({
  onLoad = loader(),
  onRefresh = vi.fn(),
  onSubmit = vi.fn(),
  revision = 3,
}: {
  onLoad?: (target: Target) => Promise<Entity>;
  onRefresh?: () => void;
  onSubmit?: (
    action: Action,
    values: Record<string, unknown>,
  ) => Promise<void> | void;
  revision?: number;
} = {}) {
  const view = render(
    <MantineProvider>
      <DiagramCommandForm
        action={action}
        kind="example-kind"
        onLoad={onLoad}
        onRefresh={onRefresh}
        onSubmit={onSubmit}
        revision={revision}
        root={root}
      />
    </MantineProvider>,
  );

  return { onLoad, onRefresh, onSubmit, view };
}

async function selectOperation(name: string) {
  await screen.findByRole("combobox", { name: "Operation" });
  fireEvent.click(screen.getByRole("option", { hidden: true, name }));
}

afterEach(cleanup);

describe("DiagramCommandForm", () => {
  it("discovers command schemas through advertised collection and self links", async () => {
    const onLoad = loader();
    renderForm({ onLoad });

    expect(
      await screen.findByRole("combobox", { name: "Operation" }),
    ).toBeVisible();
    expect(onLoad).toHaveBeenCalledTimes(2);
    expect(href(onLoad.mock.calls[0][0])).toBe("/advertised-catalogue");
    expect(href(onLoad.mock.calls[1][0])).toBe("/advertised-kind");
    expect(screen.getByRole("textbox", { name: "Id" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Label" })).toBeVisible();
  });

  it("submits a simple command with the current revision", async () => {
    const { onSubmit } = renderForm();

    fireEvent.change(await screen.findByRole("textbox", { name: "Id" }), {
      target: { value: "example-one" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Label" }), {
      target: { value: "Example one" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply command" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/advertised-command-target" }),
      {
        arguments: { id: "example-one", label: "Example one" },
        expected_revision: 3,
        operation: "add_example",
      },
    );
  });

  it("submits a command with dependent identifiers", async () => {
    const { onSubmit } = renderForm();

    await selectOperation("Connect examples");
    fireEvent.change(screen.getByRole("textbox", { name: "Id" }), {
      target: { value: "connection-one" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Source id" }), {
      target: { value: "example-one" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Target id" }), {
      target: { value: "example-two" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply command" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith(
      expect.any(Action),
      expect.objectContaining({
        arguments: expect.objectContaining({
          id: "connection-one",
          source_id: "example-one",
          target_id: "example-two",
        }),
        expected_revision: 3,
        operation: "connect_examples",
      }),
    );
  });

  it("renders advertised enum, collection, and nested object fields", async () => {
    renderForm();

    await selectOperation("Configure example");

    expect(screen.getByRole("combobox", { name: "Direction" })).toBeVisible();
    const elementIds = screen.getByRole("group", { name: "Element ids" });
    fireEvent.click(
      within(elementIds).getByRole("button", { name: "Add Item" }),
    );
    expect(within(elementIds).getByRole("textbox")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Note" })).toBeVisible();
  });

  it("keeps entered values visible when submission validation fails", async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(
        new SirenResponseError(
          422,
          "/advertised-command-target",
          "Validation failed",
          undefined,
          [],
          { arguments: "Invalid arguments" },
        ),
      );
    renderForm({ onSubmit });

    fireEvent.change(await screen.findByRole("textbox", { name: "Id" }), {
      target: { value: "example-one" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Label" }), {
      target: { value: "Keep this value" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply command" }));

    expect(await screen.findByText(/Validation failed/)).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Id" })).toHaveValue(
      "example-one",
    );
    expect(screen.getByRole("textbox", { name: "Label" })).toHaveValue(
      "Keep this value",
    );
  });

  it("offers refresh after a revision conflict and retries with the new revision", async () => {
    const onRefresh = vi.fn();
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(
        new SirenResponseError(
          409,
          "/advertised-command-target",
          "revision conflict",
        ),
      )
      .mockResolvedValueOnce(undefined);
    const onLoad = loader();
    const { view } = renderForm({
      onLoad,
      onRefresh,
      onSubmit,
      revision: 3,
    });

    fireEvent.change(await screen.findByRole("textbox", { name: "Id" }), {
      target: { value: "example-one" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply command" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Refresh diagram" }),
    );
    expect(onRefresh).toHaveBeenCalledOnce();

    view.rerender(
      <MantineProvider>
        <DiagramCommandForm
          action={action}
          kind="example-kind"
          onLoad={onLoad}
          onRefresh={onRefresh}
          onSubmit={onSubmit}
          revision={4}
          root={root}
        />
      </MantineProvider>,
    );
    fireEvent.change(await screen.findByRole("textbox", { name: "Id" }), {
      target: { value: "example-one" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply command" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(2));
    expect(onSubmit.mock.calls[1][1]).toEqual(
      expect.objectContaining({ expected_revision: 4 }),
    );
  });
});
