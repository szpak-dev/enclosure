# The gang uses its own machinery

Enclosure is not documented from a hypothetical workflow. The four repositories
that form the product family use Enclosure-registered workspace instructions in
their own development.

## What can be inspected

Each repository contains an instruction contract that requires an agent to ask
Enclosure for task-specific workspace context before work begins:

| Repository | Public instruction contract | Responsibility in the system |
| --- | --- | --- |
| Enclosure | [AGENTS.md](https://github.com/szpak-dev/enclosure/blob/main/AGENTS.md) | Connects agreement, context, and evidence to a repository workflow that requires human acceptance. |
| Mermaiden | [AGENTS.md](https://github.com/szpak-dev/mermaiden/blob/main/AGENTS.md) | Models accepted diagram intent. |
| Modwire | [AGENTS.md](https://github.com/szpak-dev/modwire/blob/main/AGENTS.md) | Measures implementation against architecture rules. |
| Sirenity | [AGENTS.md](https://github.com/szpak-dev/sirenity/blob/main/AGENTS.md) | Exposes response-scoped actions and typed navigation. |

On 17 October 2026, a live Enclosure instance resolved all four local checkouts
to registered workspaces. For a repository-specific documentation task, each
workspace returned `ready` with complete guidance coverage. The selected guidance
differed by project: Mermaiden received its module workflow, Modwire received its
operating and documentation rules, Sirenity received its workspace policy, and
Enclosure received its own service and diagram contract.

Representative public deliveries made under those repository instruction
contracts include:

| Repository | Delivered change |
| --- | --- |
| Enclosure | [PR #288: Validate supplemental budgets against selected guidance](https://github.com/szpak-dev/enclosure/pull/288) |
| Mermaiden | [PR #154: Create and verify Mermaiden's project documentation](https://github.com/szpak-dev/mermaiden/pull/154) |
| Modwire | [PR #69: Organize documentation by section](https://github.com/szpak-dev/modwire/pull/69) |
| Sirenity | [PR #263: Create initial Sirenity documentation site](https://github.com/szpak-dev/sirenity/pull/263) |

## What this proves

The observation proves that the product family is registered in a real Enclosure
instance, that each checkout can receive task-selected guidance, and that the
repositories publicly require agents to use that path. The merged changes prove
that work reached each repository's main branch.

## What this does not prove

The public pull requests do not expose private workspace identifiers or complete
context payloads. They do not prove that Enclosure caused every implementation
decision, that every historical change used the current workflow, or that a green
health report guarantees general software correctness.

This is dogfooding evidence, not a universal claim. It shows that the machinery
is used by the system that depends on it—and leaves enough of the boundary visible
for someone else to challenge the conclusion.
