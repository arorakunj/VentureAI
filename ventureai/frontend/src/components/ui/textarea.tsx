import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "min-h-[140px] w-full resize-none border border-ink/20 bg-transparent p-4 font-sans text-base leading-relaxed text-ink placeholder:text-muted-foreground/70 transition-colors duration-300 focus:border-ink focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
