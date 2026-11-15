import { expect, test, type Page } from "@playwright/test";

/** Register a fresh user, finish onboarding (which runs the first scout) and land on the inbox. */
async function onboard(page: Page) {
  const email = `e2e_${Date.now()}_${Math.floor(Math.random() * 1e6)}@example.com`;
  await page.goto("/login");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password (8+ characters)").fill("e2e-password-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Set up GigBid" })).toBeVisible();
  await page.getByLabel("Profile").selectOption("ai_ml_engineer");
  await page.getByLabel("Weekly Connects budget").fill("80");
  await page.getByRole("button", { name: "Finish and find jobs" }).click();
  await expect(page.getByRole("heading", { name: "Job inbox" })).toBeVisible({ timeout: 45_000 });
}

async function openFirstProposal(page: Page) {
  await page.getByRole("link", { name: "Open proposal" }).first().click();
  await expect(page.getByRole("heading", { name: /^Proposal:/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Approval" })).toBeVisible();
}

test("onboarding leads to a ranked inbox with recommendations", async ({ page }) => {
  await onboard(page);
  await expect(page.getByRole("link", { name: "Open proposal" }).first()).toBeVisible();
  await expect(page.getByText(/Fit \d+%/).first()).toBeVisible();
});

test("approving a proposal submits it and shows the Connects spent", async ({ page }) => {
  await onboard(page);
  await openFirstProposal(page);
  await expect(page.getByText(/Cost: \d+ Connects/)).toBeVisible();
  await page.getByRole("button", { name: "Approve and send" }).click();
  await expect(page.getByText(/Submitted \(prop-/)).toBeVisible({ timeout: 20_000 });
});

test("rejecting requires a reason and stops the proposal", async ({ page }) => {
  await onboard(page);
  await openFirstProposal(page);
  await expect(page.getByRole("button", { name: "Reject" })).toBeDisabled();
  await page.getByLabel("Reason for rejecting").fill("budget too low");
  await page.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByText("Status: rejected.")).toBeVisible({ timeout: 20_000 });
});

test("editing a draft is re-checked and blocked when it breaks policy", async ({ page }) => {
  await onboard(page);
  await openFirstProposal(page);
  const editor = page.getByLabel("Edit before sending");
  await editor.fill((await editor.inputValue()) + " I guarantee results.");
  await page.getByRole("button", { name: "Save edit and re-check" }).click();
  await expect(page.getByText(/Compliance Guard blocked this text/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("button", { name: "Approve and send" })).toBeDisabled();
});

test("a degraded-mode banner appears when the marketplace is unavailable", async ({ page }) => {
  await page.route("**/health/marketplace", (route) =>
    route.fulfill({ json: { marketplace: { ok: false, error: "connection refused" }, mode: "gigsim", profile: "offline" } }));
  await onboard(page);
  await expect(page.getByRole("alert").filter({ hasText: "Marketplace unavailable" })).toBeVisible();
});
