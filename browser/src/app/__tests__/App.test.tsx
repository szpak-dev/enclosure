import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { StrictMode, useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import type { SirenEntityProps } from "../../ui/siren/SirenEntity";
import { sirenRegistry } from "../../ui/siren/SirenRegistry";
import { App } from "../App";

const sirenClient = vi.hoisted(() => ({
  execute: vi.fn(),
  get: vi.fn(),
}));

vi.mock("../../client/SirenClient", () => ({
  SirenClient: class {
    execute = sirenClient.execute;
    get = sirenClient.get;
  },
}));

const rootEntity = {
  actions: [],
  class: ["api", "entry-point"],
  entities: [],
  links: [
    { href: "/example-siren/", rel: ["self"], title: "Enclosure API" },
    {
      href: "/example-resources",
      rel: ["collection"],
      title: "Example resources",
    },
  ],
  properties: { title: "Enclosure API" },
  title: "Enclosure API",
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/");
});

it("loads the configured root once for navigation and content", async () => {
  sirenClient.get.mockResolvedValue(rootEntity);

  const { container } = render(
    <StrictMode>
      <App rootTarget="/example-siren/" />
    </StrictMode>,
  );

  expect(container.querySelector("header")).not.toBeNull();
  expect(container.querySelector("main")).not.toBeNull();
  expect(container.querySelector("footer")).not.toBeNull();
  expect(
    await screen.findByRole("heading", { name: "Enclosure API" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Example resources" }),
  ).toBeInTheDocument();
  expect(sirenClient.get).toHaveBeenCalledTimes(1);
  expect(sirenClient.get).toHaveBeenCalledWith("/example-siren/");
});

it("loads the root once alongside a deep-linked resource", async () => {
  window.history.replaceState(null, "", "/#/example-resources");
  sirenClient.get.mockImplementation(async (target: string) =>
    target === "/example-siren/"
      ? rootEntity
      : {
          actions: [],
          class: ["example-resource"],
          entities: [],
          links: [],
          properties: {},
          title: "Current example resource",
        },
  );

  render(<App rootTarget="/example-siren/" />);

  expect(
    await screen.findByRole("heading", { name: "Current example resource" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Example resources" }),
  ).toBeInTheDocument();
  await waitFor(() => expect(sirenClient.get).toHaveBeenCalledTimes(2));
  expect(
    sirenClient.get.mock.calls.filter(
      ([target]) => target === "/example-siren/",
    ),
  ).toHaveLength(1);
});

it("loads a related resource without changing the current browser entity", async () => {
  const relatedEntity = {
    actions: [],
    class: ["related"],
    entities: [],
    links: [],
    properties: {},
    title: "Related resource",
  };
  sirenClient.get.mockImplementation(async (target: string) =>
    target === "/related"
      ? relatedEntity
      : { ...rootEntity, class: [...rootEntity.class, "background-loader"] },
  );
  function BackgroundLoader({ onLoad }: SirenEntityProps) {
    const [loaded, setLoaded] = useState(false);
    return (
      <div>
        <button
          onClick={() => void onLoad("/related").then(() => setLoaded(true))}
        >
          Load related
        </button>
        {loaded ? <span>Related resource loaded</span> : null}
      </div>
    );
  }
  const unregister = sirenRegistry.entities.register(
    "background-loader",
    BackgroundLoader,
  );

  try {
    render(<App rootTarget="/example-siren/" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Load related" }),
    );

    expect(await screen.findByText("Related resource loaded")).toBeVisible();
    expect(window.location.hash).toBe("");
    expect(sirenClient.get).toHaveBeenCalledWith("/related");
  } finally {
    unregister();
  }
});

it("shows a root failure and retries without reloading the page", async () => {
  sirenClient.get
    .mockRejectedValueOnce(new Error("Entry point unavailable"))
    .mockResolvedValueOnce(rootEntity);

  render(<App rootTarget="/example-siren/" />);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Entry point unavailable",
  );
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));

  expect(
    await screen.findByRole("heading", { name: "Enclosure API" }),
  ).toBeInTheDocument();
  expect(window.location.pathname).toBe("/");
  expect(sirenClient.get).toHaveBeenCalledTimes(2);
});

it("retries failed navigation without replacing a deep-linked resource", async () => {
  window.history.replaceState(null, "", "/#/example-resources");
  sirenClient.get.mockImplementation(async (target: string) => {
    if (target === "/example-siren/" && sirenClient.get.mock.calls.length === 1)
      throw new Error("Navigation unavailable");
    return target === "/example-siren/"
      ? rootEntity
      : {
          actions: [],
          class: ["example-resource"],
          entities: [],
          links: [],
          properties: {},
          title: "Current example resource",
        };
  });

  render(<App rootTarget="/example-siren/" />);

  expect(
    await screen.findByRole("heading", { name: "Current example resource" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("Navigation unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Retry navigation" }));

  expect(
    await screen.findByRole("link", { name: "Example resources" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Current example resource" }),
  ).toBeInTheDocument();
  expect(window.location.hash).toBe("#/example-resources");
});

it("keeps an action form mounted while showing structured submission errors", async () => {
  let rejectSubmission: (reason: unknown) => void = () => undefined;
  sirenClient.get.mockResolvedValue({
    ...rootEntity,
    actions: [
      {
        fields: [
          {
            name: "example_property",
            title: "Example property",
            type: "text",
          },
        ],
        href: "/example-resources",
        method: "POST",
        name: "create-example",
        title: "Create example",
      },
    ],
  });
  sirenClient.execute.mockReturnValue(
    new Promise((_resolve, reject) => {
      rejectSubmission = reject;
    }),
  );

  render(<App rootTarget="/example-siren/" />);

  fireEvent.click(
    await screen.findByRole("button", { name: "Create example" }),
  );
  expect(
    screen.getByRole("heading", { name: "Enclosure API" }),
  ).toBeInTheDocument();

  rejectSubmission(
    Object.assign(new Error("Validation failed"), {
      fieldErrors: { example_property: "This value is required." },
    }),
  );

  expect(await screen.findByText("This value is required.")).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Enclosure API" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("Unable to load resource")).not.toBeInTheDocument();
});

it("navigates from the root through a collection to an updated entity", async () => {
  const updatedEntity = {
    actions: [],
    class: ["example-resource"],
    entities: [],
    links: [],
    properties: { title: "Updated example" },
    title: "Updated example",
  };
  sirenClient.get.mockImplementation(async (target: string) => {
    if (target === "/example-siren/") return rootEntity;
    if (target === "/example-resources")
      return {
        actions: [],
        class: ["collection", "example-resource"],
        entities: [
          {
            class: ["example-resource"],
            links: [
              {
                href: "/example-resources/one",
                rel: ["self"],
                title: "Example one",
              },
            ],
            properties: { title: "Example one" },
            rel: ["item"],
            title: "Example one",
          },
        ],
        links: [],
        properties: {},
        title: "Example resources",
      };
    return {
      actions: [
        {
          fields: [{ name: "title", title: "Title", type: "text" }],
          href: "/example-resources/one",
          method: "PUT",
          name: "update-example",
          title: "Update example",
        },
      ],
      class: ["example-resource"],
      entities: [],
      links: [],
      properties: { title: "Example one" },
      title: "Example one",
    };
  });
  sirenClient.execute.mockResolvedValue(updatedEntity);

  render(<App rootTarget="/example-siren/" />);

  fireEvent.click(
    await screen.findByRole("link", { name: "Example resources" }),
  );
  fireEvent.click(await screen.findByRole("link", { name: "Example one" }));
  fireEvent.change(await screen.findByRole("textbox"), {
    target: { value: "Updated example" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Update example" }));

  expect(
    await screen.findByRole("heading", { name: "Updated example" }),
  ).toBeInTheDocument();
  expect(sirenClient.execute).toHaveBeenCalledWith(
    expect.objectContaining({ name: "update-example" }),
    { title: "Updated example" },
  );
  expect(window.location.hash).toBe("#/example-resources/one");
});

it("creates an entity from an advertised root action", async () => {
  const createdEntity = {
    actions: [],
    class: ["example-resource"],
    entities: [],
    links: [],
    properties: { title: "Created example" },
    title: "Created example",
  };
  sirenClient.get.mockResolvedValue({
    ...rootEntity,
    actions: [
      {
        fields: [{ name: "title", title: "Title", type: "text" }],
        href: "/example-resources",
        method: "POST",
        name: "create-example",
        title: "Create example",
      },
    ],
  });
  sirenClient.execute.mockResolvedValue(createdEntity);

  render(<App rootTarget="/example-siren/" />);

  fireEvent.change(await screen.findByRole("textbox"), {
    target: { value: "Created example" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create example" }));

  expect(
    await screen.findByRole("heading", { name: "Created example" }),
  ).toBeInTheDocument();
  expect(sirenClient.execute).toHaveBeenCalledWith(
    expect.objectContaining({ name: "create-example" }),
    { title: "Created example" },
  );
});

it("renders a command representation from an advertised action", async () => {
  window.history.replaceState(null, "", "/#/example-resources/one");
  const detailEntity = {
    actions: [
      {
        fields: [{ name: "format", title: "Format", type: "text" }],
        href: "/example-resources/one/renderings",
        method: "POST",
        name: "render-example",
        title: "Render example",
      },
    ],
    class: ["example-resource"],
    entities: [],
    links: [],
    properties: {},
    title: "Example one",
  };
  sirenClient.get.mockImplementation(async (target: string) =>
    target === "/example-siren/" ? rootEntity : detailEntity,
  );
  sirenClient.execute.mockResolvedValue({
    actions: [],
    class: ["command"],
    entities: [],
    links: [],
    properties: { content: "Rendered content" },
    title: "Rendered example",
  });

  render(<App rootTarget="/example-siren/" />);

  fireEvent.change(await screen.findByRole("textbox"), {
    target: { value: "markdown" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Render example" }));

  expect(
    await screen.findByRole("heading", { name: "Rendered example" }),
  ).toBeInTheDocument();
  expect(sirenClient.execute).toHaveBeenCalledWith(
    expect.objectContaining({ name: "render-example" }),
    { format: "markdown" },
  );
});

it("reloads the current resource after a content-free action", async () => {
  window.history.replaceState(null, "", "/#/example-resources/one");
  const detailEntity = {
    actions: [
      {
        fields: [],
        href: "/example-resources/one",
        method: "DELETE",
        name: "delete-example",
        title: "Delete example",
      },
    ],
    class: ["example-resource"],
    entities: [],
    links: [],
    properties: {},
    title: "Example one",
  };
  sirenClient.get.mockImplementation(async (target: string) =>
    target === "/example-siren/" ? rootEntity : detailEntity,
  );
  sirenClient.execute.mockResolvedValue(null);

  render(<App rootTarget="/example-siren/" />);

  fireEvent.click(
    await screen.findByRole("button", { name: "Delete example" }),
  );

  await waitFor(() =>
    expect(
      sirenClient.get.mock.calls.filter(
        ([target]) => target === "/example-resources/one",
      ),
    ).toHaveLength(2),
  );
  expect(sirenClient.execute).toHaveBeenCalledWith(
    expect.objectContaining({ name: "delete-example" }),
    {},
  );
});
