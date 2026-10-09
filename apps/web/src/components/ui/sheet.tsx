import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Sidebar drawer for viewports too narrow for a persistent sidebar.
 * Built on Radix Dialog so focus trapping, Escape-to-close and scroll locking
 * are correct without hand-rolling them.
 */
const Sheet = DialogPrimitive.Root;
const SheetTrigger = DialogPrimitive.Trigger;
const SheetClose = DialogPrimitive.Close;
const SheetPortal = DialogPrimitive.Portal;

const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
    side?: "left" | "right";
  }
>(({ side = "left", className, children, ...props }, ref) => (
  <SheetPortal>
    <DialogPrimitive.Overlay
      className={cn(
        "fixed inset-0 z-50 bg-black/70 backdrop-blur-sm",
        "data-[state=open]:animate-in data-[state=open]:fade-in-0",
        "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
      )}
    />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed inset-y-0 z-50 flex h-full w-[280px] flex-col border-white/10 bg-abyss-900 shadow-2xl",
        "data-[state=open]:animate-in data-[state=closed]:animate-out duration-200",
        side === "left"
          ? "left-0 border-r data-[state=open]:slide-in-from-left data-[state=closed]:slide-out-to-left"
          : "right-0 border-l data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
        className,
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close
        className="absolute right-3 top-3 rounded-md p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-hot"
        aria-label="Close navigation"
      >
        <X className="size-4" aria-hidden="true" />
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </SheetPortal>
));
SheetContent.displayName = "SheetContent";

const SheetTitle = DialogPrimitive.Title;
const SheetDescription = DialogPrimitive.Description;

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetTitle,
  SheetDescription,
  SheetPortal,
};