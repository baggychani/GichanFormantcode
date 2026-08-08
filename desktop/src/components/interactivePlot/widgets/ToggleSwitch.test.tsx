import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ToggleSwitch } from "./ToggleSwitch";

describe("ToggleSwitch", () => {
  it("exposes binary settings as a switch and activates them", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ToggleSwitch label="격자 표시" checked={false} onChange={onChange} />);

    const control = screen.getByRole("switch", { name: "격자 표시" });
    expect(control).toHaveAttribute("aria-checked", "false");
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();

    await user.click(control);

    expect(onChange).toHaveBeenCalledOnce();
  });

  it("does not activate while disabled", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ToggleSwitch label="타원 표시" checked onChange={onChange} disabled />);

    const control = screen.getByRole("switch", { name: "타원 표시" });
    expect(control).toBeDisabled();
    expect(control).toHaveAttribute("aria-checked", "true");

    await user.click(control);

    expect(onChange).not.toHaveBeenCalled();
  });
});
