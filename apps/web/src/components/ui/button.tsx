import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium " +
    "transition-[background-color,border-color,color,transform,box-shadow] duration-150 " +
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-hot " +
    "disabled:pointer-events-none disabled:opacity-45 [&_svg]:shrink-0 [&_svg]:pointer-events-none",
  {
    variants: {
      variant: {
        // Primary is the crimson brand action.
        default:
          "bg-brand-500 text-white shadow-[0_6px_20px_-8px_rgba(239,35,60,0.7)] " +
          "hover:bg-brand-hot active:scale-[0.97]",
        secondary:
          "bg-white/[0.06] text-white/90 border border-white/10 hover:bg-white/[0.10] " +
          "hover:border-white/20 active:scale-[0.97]",
        outline:
          "border border-white/12 text-white/80 hover:text-white hover:border-brand-500/60 " +
          "hover:bg-brand-500/[0.07]",
        ghost: "text-white/65 hover:text-white hover:bg-white/[0.06]",
        danger:
          "bg-semantic-block/15 text-semantic-block border border-semantic-block/45 " +
          "hover:bg-semantic-block/25",
        link: "text-brand-400 underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-xs [&_svg]:size-3.5",
        default: "h-10 px-5 [&_svg]:size-4",
        lg: "h-12 px-7 text-base [&_svg]:size-[18px]",
        icon: "size-9 [&_svg]:size-4",
        "icon-sm": "size-7 [&_svg]:size-3.5",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        // Default to "button": a bare <button> inside a form submits by default,
        // which has bitten every chat composer ever built.
        type={asChild ? undefined : (type ?? "button")}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };