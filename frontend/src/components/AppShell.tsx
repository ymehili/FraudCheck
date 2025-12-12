"use client";

import { type ReactNode } from "react";
import { NavigationBar } from "@/components/NavigationBar";
import { cn } from "@/lib/utils";

export function AppShell({
  children,
  className,
  contentClassName,
}: {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <div className={cn("app-shell", className)}>
      <NavigationBar />
      <main className={cn("app-container app-section", contentClassName)}>{children}</main>
    </div>
  );
}





