import type { Metadata } from "next";
import { ClerkProvider } from '@clerk/nextjs';
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ErrorBoundary } from '@/components/ui/error-boundary';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CheckGuard AI - Advanced Check Fraud Detection & Prevention",
  description: "Protect your business with AI-powered check fraud detection. Advanced image forensics, OCR analysis, and real-time risk assessment. 99.2% accuracy, under 3 seconds processing. Start free trial.",
  keywords: "check fraud detection, AI fraud prevention, image forensics, OCR analysis, financial security, fraud protection, risk assessment, business protection",
  authors: [{ name: "CheckGuard AI" }],
  creator: "CheckGuard AI",
  publisher: "CheckGuard AI",
  robots: "index, follow",
  openGraph: {
    title: "CheckGuard AI - Advanced Check Fraud Detection",
    description: "Protect your business from fraudulent checks using cutting-edge AI forensics. Get instant risk assessments with 99.2% accuracy.",
    url: "https://checkguard.ai",
    siteName: "CheckGuard AI",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "CheckGuard AI - Check Fraud Detection System",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CheckGuard AI - Advanced Check Fraud Detection",
    description: "AI-powered fraud detection with 99.2% accuracy. Protect your business from fraudulent checks.",
    images: ["/twitter-image.jpg"],
    creator: "@checkguardai",
  },
  viewport: "width=device-width, initial-scale=1",
  themeColor: "#2563eb",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body
          className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-background font-sans antialiased`}
        >
          <ErrorBoundary showDetails={process.env.NODE_ENV === 'development'}>
            {children}
          </ErrorBoundary>
        </body>
      </html>
    </ClerkProvider>
  );
}
