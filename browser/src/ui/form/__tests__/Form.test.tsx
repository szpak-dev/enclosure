import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Form } from "../Form";
import { FormField } from "../FormField";

afterEach(cleanup);

it("preserves falsy and empty form values", async () => {
  const onSubmit = vi.fn();

  render(
    <MantineProvider>
      <Form
        controls={[
          { name: "enabled", valueType: "boolean" },
          { name: "limit", valueType: "number" },
          { name: "description" },
        ]}
        onSubmit={onSubmit}
      >
        {() => (
          <>
            <input name="enabled" type="checkbox" />
            <input defaultValue="0" name="limit" type="number" />
            <input defaultValue="" name="description" type="text" />
            <button type="submit">Submit</button>
          </>
        )}
      </Form>
    </MantineProvider>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Submit" }));

  await waitFor(() =>
    expect(onSubmit).toHaveBeenCalledWith({
      description: "",
      enabled: false,
      limit: 0,
    }),
  );
});

it("shows submission violations beside their fields", async () => {
  const error = Object.assign(new Error("Validation failed"), {
    fieldErrors: { example_property: "This value is required." },
  });

  render(
    <MantineProvider>
      <Form
        controls={[{ name: "example_property" }]}
        onSubmit={vi.fn().mockRejectedValue(error)}
      >
        {(errors) => (
          <>
            <FormField
              {...(errors.example_property
                ? { error: errors.example_property }
                : {})}
              label="Example property"
            >
              <input name="example_property" />
            </FormField>
            <button type="submit">Submit</button>
          </>
        )}
      </Form>
    </MantineProvider>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Submit" }));

  expect(await screen.findByText("This value is required.")).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent("Validation failed");
});
