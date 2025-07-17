import Link from "next/link";
import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/nextjs";
import Button from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">CheckGuard AI</h1>
            </div>
            <div className="flex items-center space-x-4">
              <SignedIn>
                <Link href="/upload">
                  <Button variant="primary" size="sm">
                    Upload Check
                  </Button>
                </Link>
                <UserButton afterSignOutUrl="/" />
              </SignedIn>
              <SignedOut>
                <SignInButton mode="modal">
                  <Button variant="primary" size="sm">
                    Sign In
                  </Button>
                </SignInButton>
              </SignedOut>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <h2 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
            AI-Powered Check Fraud Detection
          </h2>
          <p className="mt-6 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
            Protect your business from fraudulent checks using advanced image analysis and machine learning. 
            Upload check images for instant fraud detection and risk assessment.
          </p>
          
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <SignedIn>
              <Link href="/upload">
                <Button variant="primary" size="lg">
                  Start Analysis
                </Button>
              </Link>
            </SignedIn>
            <SignedOut>
              <SignInButton mode="modal">
                <Button variant="primary" size="lg">
                  Get Started
                </Button>
              </SignInButton>
            </SignedOut>
          </div>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-2">Image Analysis</h3>
              <p className="text-muted-foreground">
                Advanced computer vision algorithms analyze check images for signs of tampering, alteration, or forgery.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-2">OCR Extraction</h3>
              <p className="text-muted-foreground">
                Extract and verify key information like amounts, dates, signatures, and account numbers automatically.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-foreground mb-2">Risk Scoring</h3>
              <p className="text-muted-foreground">
                Get comprehensive risk assessments with detailed reports and actionable insights.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>

      <footer className="bg-gray-50 border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-500">
            © 2024 CheckGuard AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
