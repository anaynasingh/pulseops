import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProposedTasksBell } from "@/components/layout/ProposedTasksBell";
import { proposedTasksApi } from "@/lib/api";
import type { ProposedTask, ProposedTaskConfirmResult } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  proposedTasksApi: {
    list: vi.fn(),
    count: vi.fn(),
    confirm: vi.fn(),
  },
}));

const mockedApi = vi.mocked(proposedTasksApi);

const makeProposal = (overrides: Partial<ProposedTask>): ProposedTask => ({
  id: "00000000-0000-0000-0000-000000000000",
  transcript_id: "11111111-1111-1111-1111-111111111111",
  meeting_title: "Sprint Planning",
  meeting_date: "2026-07-20",
  title: "Untitled action item",
  description: null,
  priority: "medium",
  assignee_hint: null,
  status: "pending",
  dedup_status: null,
  created_task_id: null,
  proposed_at: "2026-07-20T10:00:00Z",
  ...overrides,
});

const p1 = makeProposal({
  id: "aaaaaaaa-0000-0000-0000-000000000001",
  title: "Update the deployment runbook",
  priority: "high",
  assignee_hint: "Anayna",
});
const p2 = makeProposal({
  id: "aaaaaaaa-0000-0000-0000-000000000002",
  title: "Schedule QA migration dry run",
});
const p3 = makeProposal({
  id: "aaaaaaaa-0000-0000-0000-000000000003",
  meeting_title: "Client Sync",
  meeting_date: "2026-07-21",
  title: "Send revised proposal to client",
  priority: "urgent",
});

const confirmResult = (
  overrides: Partial<ProposedTaskConfirmResult> = {}
): ProposedTaskConfirmResult => ({
  created: 0,
  skipped_duplicates: 0,
  dismissed: 0,
  tasks: [],
  results: [],
  ...overrides,
});

function renderBell() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProposedTasksBell />
    </QueryClientProvider>
  );
}

async function openPanel(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Proposed tasks" }));
  await waitFor(() =>
    expect(screen.getByRole("dialog", { name: "Proposed tasks panel" })).toBeInTheDocument()
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.count.mockResolvedValue({ pending: 3 });
  mockedApi.list.mockResolvedValue([p1, p2, p3]);
  mockedApi.confirm.mockResolvedValue(confirmResult());
});

describe("ProposedTasksBell", () => {
  it("shows the pending count as a badge on the bell", async () => {
    renderBell();
    const bell = screen.getByRole("button", { name: "Proposed tasks" });
    await waitFor(() => expect(within(bell).getByText("3")).toBeInTheDocument());
    expect(mockedApi.count).toHaveBeenCalled();
  });

  it("groups panel items by meeting_title and meeting_date", async () => {
    const user = userEvent.setup();
    renderBell();
    await openPanel(user);

    await waitFor(() => expect(screen.getByText("Sprint Planning")).toBeInTheDocument());
    expect(screen.getByText("Client Sync")).toBeInTheDocument();
    expect(screen.getByText("20 Jul 2026")).toBeInTheDocument();
    expect(screen.getByText("21 Jul 2026")).toBeInTheDocument();

    // Sprint Planning group contains its two items; Client Sync contains one
    expect(screen.getByText("Update the deployment runbook")).toBeInTheDocument();
    expect(screen.getByText("Schedule QA migration dry run")).toBeInTheDocument();
    expect(screen.getByText("Send revised proposal to client")).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
  });

  it("renders all checkboxes checked by default", async () => {
    const user = userEvent.setup();
    renderBell();
    await openPanel(user);

    await waitFor(() => expect(screen.getAllByRole("checkbox")).toHaveLength(3));
    for (const checkbox of screen.getAllByRole("checkbox")) {
      expect(checkbox).toBeChecked();
    }
    expect(
      screen.getByRole("button", { name: "Add selected (3)" })
    ).toBeInTheDocument();
  });

  it("Add selected sends only checked ids; unchecked items stay pending and rendered", async () => {
    // After confirming p1 + p3, the refetched pending list contains only p2
    mockedApi.list
      .mockResolvedValueOnce([p1, p2, p3])
      .mockResolvedValue([p2]);
    mockedApi.confirm.mockResolvedValue(
      confirmResult({ created: 2, results: [] })
    );

    const user = userEvent.setup();
    renderBell();
    await openPanel(user);

    await waitFor(() => expect(screen.getAllByRole("checkbox")).toHaveLength(3));
    await user.click(
      screen.getByRole("checkbox", { name: "Select Schedule QA migration dry run" })
    );
    await user.click(screen.getByRole("button", { name: "Add selected (2)" }));

    await waitFor(() =>
      expect(mockedApi.confirm).toHaveBeenCalledWith([p1.id, p3.id], [])
    );
    // The unchecked id must NOT appear anywhere in the confirm payload
    const [acceptedIds, dismissedIds] = mockedApi.confirm.mock.calls[0];
    expect(acceptedIds).not.toContain(p2.id);
    expect(dismissedIds).toEqual([]);

    // Unchecked item remains pending and still rendered after refetch
    await waitFor(() =>
      expect(mockedApi.list).toHaveBeenCalledTimes(2)
    );
    await waitFor(() =>
      expect(screen.getByText("Schedule QA migration dry run")).toBeInTheDocument()
    );
    expect(screen.queryByText("Update the deployment runbook")).not.toBeInTheDocument();
  });

  it("per-item dismiss sends only that id in dismissed_ids", async () => {
    const user = userEvent.setup();
    renderBell();
    await openPanel(user);

    await waitFor(() =>
      expect(screen.getByText("Update the deployment runbook")).toBeInTheDocument()
    );
    await user.click(
      screen.getByRole("button", { name: "Dismiss Update the deployment runbook" })
    );

    await waitFor(() =>
      expect(mockedApi.confirm).toHaveBeenCalledWith([], [p1.id])
    );
  });

  it("Dismiss unchecked sends the explicitly unchecked ids as dismissed_ids", async () => {
    const user = userEvent.setup();
    renderBell();
    await openPanel(user);

    await waitFor(() => expect(screen.getAllByRole("checkbox")).toHaveLength(3));
    const dismissUnchecked = screen.getByRole("button", { name: "Dismiss unchecked" });
    // Nothing unchecked yet — button is disabled, no implicit dismissal possible
    expect(dismissUnchecked).toBeDisabled();

    await user.click(
      screen.getByRole("checkbox", { name: "Select Send revised proposal to client" })
    );
    await user.click(dismissUnchecked);

    await waitFor(() =>
      expect(mockedApi.confirm).toHaveBeenCalledWith([], [p3.id])
    );
  });

  it("shows the empty state when there are no pending proposals", async () => {
    mockedApi.count.mockResolvedValue({ pending: 0 });
    mockedApi.list.mockResolvedValue([]);

    const user = userEvent.setup();
    renderBell();
    await openPanel(user);

    await waitFor(() =>
      expect(
        screen.getByText(/No proposed tasks\. You're all caught up\./)
      ).toBeInTheDocument()
    );
    // No badge when nothing is pending
    const bell = screen.getByRole("button", { name: "Proposed tasks" });
    expect(within(bell).queryByText("0")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Add selected/ })
    ).not.toBeInTheDocument();
  });
});
