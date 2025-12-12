import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const API_BASE_URL =
  process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";

interface RouteParams {
  params: Promise<{
    id: string;
  }>;
}

export async function GET(_request: NextRequest, { params }: RouteParams) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;
    if (!id) {
      return NextResponse.json({ error: "Analysis id is required" }, { status: 400 });
    }

    const backendResponse = await fetch(`${API_BASE_URL}/api/v1/analyze/${id}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({
        detail: `Backend error: ${backendResponse.statusText}`,
      }));
      return NextResponse.json(
        { error: errorData.message || errorData.detail || "Failed to load analysis", ...errorData },
        { status: backendResponse.status }
      );
    }

    return NextResponse.json(await backendResponse.json());
  } catch (error) {
    console.error("Analysis API route error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}


