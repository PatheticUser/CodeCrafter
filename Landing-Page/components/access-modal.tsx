"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export function AccessModal() {
  const [open, setOpen] = useState(false)

  const handleSendEmail = () => {
    window.location.href = "mailto:rameezalipacific@gmail.com"
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="lg" className="transition-transform hover:-translate-y-0.5 cursor-none">
          Try CodeCrafter
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Repository Access</DialogTitle>
          <DialogDescription className="pt-2">
            <div className="text-foreground font-medium mb-3">Thank you for your interest in CodeCrafter.</div>
            <div className="text-muted-foreground mb-4">
              Our repository is currently in private access to ensure code quality and controlled distribution. To gain
              access to the source code and project details, please reach out to us directly.
            </div>
            <div className="text-muted-foreground">
              <span className="text-foreground font-semibold">Email:</span>{" "}
              <a href="mailto:rameezalipacific@gmail.com" className="text-primary hover:underline">
                rameezalipacific@gmail.com
              </a>
            </div>
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Close
          </Button>
          <Button onClick={handleSendEmail} className="bg-primary hover:bg-primary/90">
            Send Email
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
