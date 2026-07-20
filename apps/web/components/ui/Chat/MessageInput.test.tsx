import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MessageInput from './MessageInput';

describe('MessageInput', () => {
  it('AC6: Enter submits and clears the input', () => {
    const onSubmit = vi.fn();
    render(<MessageInput onSubmit={onSubmit} disabled={false} />);

    const textarea = screen.getByPlaceholderText(/ask aria/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'hello there' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSubmit).toHaveBeenCalledWith('hello there');
    expect(textarea.value).toBe('');
  });

  it('AC6: Shift+Enter inserts a newline instead of submitting', () => {
    const onSubmit = vi.fn();
    render(<MessageInput onSubmit={onSubmit} disabled={false} />);

    const textarea = screen.getByPlaceholderText(/ask aria/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not submit an empty/whitespace-only message', () => {
    const onSubmit = vi.fn();
    render(<MessageInput onSubmit={onSubmit} disabled={false} />);

    const textarea = screen.getByPlaceholderText(/ask aria/i);
    fireEvent.change(textarea, { target: { value: '   ' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSubmit).not.toHaveBeenCalled();
  });
});
