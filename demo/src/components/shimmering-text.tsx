"use client";

import { motion } from "motion/react";
import { type ComponentProps } from "react";
import { cn } from "@/lib/utils";

export type ShimmeringTextProps = Omit<
  ComponentProps<typeof motion.span>,
  "children"
> & {
  text: string;
  /** Legacy animation options retained for chart component compatibility. */
  duration?: number;
  paused?: boolean;
  isStopped?: boolean;
};

/** Keep chart loading labels readable; the recording trace owns the motion. */
export function ShimmeringText({
  text,
  duration: _duration,
  isStopped: _isStopped,
  paused: _paused,
  className,
  ...props
}: ShimmeringTextProps) {
  return (
    <motion.span
      className={cn("inline-flex items-center text-muted-foreground", className)}
      {...props}
    >
      {text}
    </motion.span>
  );
}
