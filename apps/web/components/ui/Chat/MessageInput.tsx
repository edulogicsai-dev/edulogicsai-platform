'use client';

import { useState, KeyboardEvent } from 'react';
import Button from '@/components/ui/Button';

interface MessageInputProps {
  onSubmit: (message: string) => void;
  disabled: boolean;
}

export default function MessageInput({ onSubmit, disabled }: MessageInputProps) {
  const [value, setValue] = useState('');

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
  };

  // AC6: Enter submits, Shift+Enter inserts a newline.
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Ask ARIA, MIRA, or QUINN..."
        className="flex-1 p-3 rounded-md bg-zinc-800 resize-none disabled:opacity-50"
      />
      <Button
        variant="slim"
        type="button"
        disabled={disabled || !value.trim()}
        onClick={submit}
      >
        Send
      </Button>
    </div>
  );
}
