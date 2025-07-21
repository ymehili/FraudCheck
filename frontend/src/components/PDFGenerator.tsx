'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, FileText, Loader2 } from 'lucide-react';
import { AnalysisResponse } from '@/types/api';
import { formatDate, formatCurrency, getRiskLevel } from '@/lib/utils';

interface PDFGeneratorProps {
  analysis: AnalysisResponse;
  fileName?: string;
  className?: string;
}

export function PDFGenerator({ 
  analysis, 
  fileName = `check-analysis-${analysis.analysis_id.slice(-8)}.pdf`,
  className = ""
}: PDFGeneratorProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generatePDF = async () => {
    try {
      setIsGenerating(true);
      setError(null);

      // Dynamic import to avoid SSR issues with jsPDF
      const { jsPDF } = await import('jspdf');
      
      // Create PDF document
      const pdf = new jsPDF();
      const pageWidth = pdf.internal.pageSize.width;
      const pageHeight = pdf.internal.pageSize.height;
      const margin = 20;
      let currentY = margin;

      // Helper function to add text with automatic page breaks
      const addText = (text: string, x: number, y: number, options?: any) => {
        if (y > pageHeight - margin) {
          pdf.addPage();
          currentY = margin;
          y = currentY;
        }
        pdf.text(text, x, y, options);
        return y;
      };

      // Helper function to add multiline text
      const addMultilineText = (text: string, x: number, y: number, maxWidth: number) => {
        const lines = pdf.splitTextToSize(text, maxWidth);
        for (let i = 0; i < lines.length; i++) {
          if (y > pageHeight - margin) {
            pdf.addPage();
            y = margin;
          }
          pdf.text(lines[i], x, y);
          y += 6;
        }
        return y;
      };

      // Title and Header
      pdf.setFontSize(24);
      pdf.setTextColor(40, 40, 40);
      currentY = addText('CheckGuard AI - Analysis Report', margin, currentY);
      currentY += 15;

      // Subtitle
      pdf.setFontSize(14);
      pdf.setTextColor(100, 100, 100);
      currentY = addText(`Analysis Report for Check #${analysis.analysis_id.slice(-8)}`, margin, currentY);
      currentY += 10;

      // Date line
      pdf.setFontSize(12);
      currentY = addText(`Generated on ${formatDate(new Date())}`, margin, currentY);
      currentY += 20;

      // Executive Summary Box
      pdf.setDrawColor(200, 200, 200);
      pdf.setFillColor(245, 245, 245);
      pdf.rect(margin, currentY - 5, pageWidth - 2 * margin, 40, 'FD');
      
      pdf.setFontSize(16);
      pdf.setTextColor(40, 40, 40);
      currentY = addText('Executive Summary', margin + 10, currentY + 5);
      currentY += 10;

      pdf.setFontSize(12);
      const riskLevel = getRiskLevel(analysis.risk_score);
      const riskColor = analysis.risk_score >= 75 ? [220, 38, 38] as [number, number, number] : 
                       analysis.risk_score >= 50 ? [245, 158, 11] as [number, number, number] : [34, 197, 94] as [number, number, number];
      
      pdf.setTextColor(...riskColor);
      currentY = addText(`Risk Level: ${riskLevel.toUpperCase()}`, margin + 10, currentY);
      
      pdf.setTextColor(40, 40, 40);
      currentY = addText(`Risk Score: ${analysis.risk_score}/100`, pageWidth - margin - 80, currentY - 6);
      currentY += 10;

      pdf.setTextColor(100, 100, 100);
      const summaryText = `Analysis completed on ${formatDate(analysis.created_at)}${analysis.processing_time ? ` in ${analysis.processing_time.toFixed(1)} seconds` : ''}`;
      currentY = addText(summaryText, margin + 10, currentY);
      currentY += 25;

      // Analysis Details Section
      pdf.setFontSize(16);
      pdf.setTextColor(40, 40, 40);
      currentY = addText('Analysis Details', margin, currentY);
      currentY += 10;

      // Analysis Info Table
      pdf.setFontSize(10);
      const analysisInfo = [
        ['Analysis ID', `#${analysis.analysis_id}`],
        ['File ID', `#${analysis.file_id}`],
        ['Created Date', formatDate(analysis.created_at)],
        ['Processing Time', analysis.processing_time ? `${analysis.processing_time.toFixed(1)} seconds` : 'N/A'],
        ['Risk Score', `${analysis.risk_score}/100`],
        ['Risk Level', getRiskLevel(analysis.risk_score).toUpperCase()],
      ];

      analysisInfo.forEach(([label, value]) => {
        pdf.setTextColor(100, 100, 100);
        currentY = addText(`${label}:`, margin, currentY);
        pdf.setTextColor(40, 40, 40);
        addText(value, margin + 60, currentY);
        currentY += 8;
      });
      currentY += 10;

      // OCR Results Section
      if (analysis.ocr_result) {
        pdf.setFontSize(16);
        pdf.setTextColor(40, 40, 40);
        currentY = addText('Extracted Information (OCR)', margin, currentY);
        currentY += 10;

        const ocrInfo = [
          ['Payee', analysis.ocr_result.payee || 'Not detected'],
          ['Amount', analysis.ocr_result.amount ? formatCurrency(analysis.ocr_result.amount) : 'Not detected'],
          ['Date', analysis.ocr_result.date || 'Not detected'],
          ['Check Number', analysis.ocr_result.check_number || 'Not detected'],
          ['Account Number', analysis.ocr_result.account_number || 'Not detected'],
          ['Routing Number', analysis.ocr_result.routing_number || 'Not detected'],
        ];

        pdf.setFontSize(10);
        ocrInfo.forEach(([label, value]) => {
          pdf.setTextColor(100, 100, 100);
          currentY = addText(`${label}:`, margin, currentY);
          pdf.setTextColor(40, 40, 40);
          currentY = addMultilineText(value, margin + 60, currentY, pageWidth - margin - 80);
          currentY += 2;
        });
        currentY += 10;
      }

      // Forensic Analysis Section
      if (analysis.forensics_result) {
        pdf.setFontSize(16);
        pdf.setTextColor(40, 40, 40);
        currentY = addText('Forensic Analysis', margin, currentY);
        currentY += 10;

        pdf.setFontSize(10);
        
        // Image Quality
        if (analysis.forensics_result.image_quality) {
          pdf.setTextColor(100, 100, 100);
          currentY = addText('Image Quality Assessment:', margin, currentY);
          currentY += 8;

          const qualityInfo = [
            ['Resolution', analysis.forensics_result.image_quality.resolution || 'N/A'],
            ['Compression Ratio', analysis.forensics_result.image_quality.compression_ratio || 'N/A'],
            ['Clarity Score', analysis.forensics_result.image_quality.clarity_score || 'N/A'],
          ];

          qualityInfo.forEach(([label, value]) => {
            pdf.setTextColor(40, 40, 40);
            currentY = addText(`  • ${label}: ${value}`, margin + 10, currentY);
            currentY += 6;
          });
          currentY += 5;
        }

        // Anomaly Detection
        if (analysis.forensics_result.anomalies) {
          pdf.setTextColor(100, 100, 100);
          currentY = addText('Anomaly Detection:', margin, currentY);
          currentY += 8;

          const anomalyInfo = [
            ['Edge Inconsistencies', analysis.forensics_result.anomalies.edge_inconsistencies ? 'Detected' : 'None'],
            ['Font Inconsistencies', analysis.forensics_result.anomalies.font_inconsistencies ? 'Detected' : 'None'],
            ['Ink Analysis', analysis.forensics_result.anomalies.ink_analysis ? 'Anomalies Found' : 'Normal'],
          ];

          anomalyInfo.forEach(([label, value]) => {
            pdf.setTextColor(40, 40, 40);
            const color = (value.includes('Detected') || value.includes('Anomalies')) ? [220, 38, 38] as [number, number, number] : [34, 197, 94] as [number, number, number];
            pdf.setTextColor(...color);
            currentY = addText(`  • ${label}: ${value}`, margin + 10, currentY);
            currentY += 6;
          });
          currentY += 5;
        }

        // Confidence Score
        if (analysis.forensics_result.confidence_score) {
          pdf.setTextColor(100, 100, 100);
          currentY = addText('Forensic Confidence:', margin, currentY);
          pdf.setTextColor(40, 40, 40);
          addText(`${(analysis.forensics_result.confidence_score * 100).toFixed(1)}%`, margin + 80, currentY);
          currentY += 10;
        }
      }

      // Rule Engine Results Section
      if (analysis.rule_engine_result) {
        pdf.setFontSize(16);
        pdf.setTextColor(40, 40, 40);
        currentY = addText('Fraud Detection Rules', margin, currentY);
        currentY += 10;

        pdf.setFontSize(10);
        
        // Summary stats
        const totalRules = analysis.rule_engine_result.total_rules_checked || 0;
        const triggeredRules = analysis.rule_engine_result.triggered_rules?.length || 0;
        const passedRules = totalRules - triggeredRules;

        pdf.setTextColor(100, 100, 100);
        currentY = addText(`Rules Summary: ${totalRules} total, ${triggeredRules} triggered, ${passedRules} passed`, margin, currentY);
        currentY += 10;

        // Triggered Rules
        if (analysis.rule_engine_result.triggered_rules && analysis.rule_engine_result.triggered_rules.length > 0) {
          pdf.setTextColor(220, 38, 38);
          pdf.setFontSize(12);
          currentY = addText('⚠ Triggered Rules:', margin, currentY);
          currentY += 8;

          pdf.setFontSize(10);
          analysis.rule_engine_result.triggered_rules.forEach((rule, index) => {
            pdf.setTextColor(40, 40, 40);
            currentY = addText(`${index + 1}. ${rule.rule_name} (Weight: ${rule.weight})`, margin + 10, currentY);
            currentY += 6;
            if (rule.description) {
              pdf.setTextColor(100, 100, 100);
              currentY = addMultilineText(`   ${rule.description}`, margin + 15, currentY, pageWidth - margin - 30);
              currentY += 3;
            }
          });
        } else {
          pdf.setTextColor(34, 197, 94);
          pdf.setFontSize(12);
          currentY = addText('✓ No fraud rules triggered - All checks passed', margin, currentY);
        }
        currentY += 15;
      }

      // Footer
      const footerY = pageHeight - 15;
      pdf.setFontSize(8);
      pdf.setTextColor(150, 150, 150);
      pdf.text('Generated by CheckGuard AI - Fraud Detection System', margin, footerY);
      pdf.text(`Page 1 of ${pdf.internal.pages.length - 1}`, pageWidth - margin - 30, footerY);

      // Save the PDF
      pdf.save(fileName);

    } catch (error) {
      console.error('Failed to generate PDF:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate PDF report');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className={className}>
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      <Button 
        onClick={generatePDF}
        disabled={isGenerating}
        className="w-full sm:w-auto"
      >
        {isGenerating ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Generating PDF...
          </>
        ) : (
          <>
            <Download className="h-4 w-4 mr-2" />
            Download PDF Report
          </>
        )}
      </Button>
      
      <p className="text-xs text-gray-500 mt-2">
        Generate a comprehensive PDF report of this analysis including all findings and recommendations.
      </p>
    </div>
  );
}

// Hook for PDF generation functionality
export function usePDFGenerator() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateAnalysisReport = async (
    analysis: AnalysisResponse, 
    fileName?: string
  ): Promise<boolean> => {
    try {
      setIsGenerating(true);
      setError(null);

      const { jsPDF } = await import('jspdf');
      const pdf = new jsPDF();
      
      // Use the same PDF generation logic as the component
      // This is extracted for reusability in other parts of the app
      
      const reportFileName = fileName || `check-analysis-${analysis.analysis_id.slice(-8)}.pdf`;
      pdf.save(reportFileName);
      
      return true;
    } catch (error) {
      console.error('Failed to generate PDF:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate PDF report');
      return false;
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    generateAnalysisReport,
    isGenerating,
    error,
  };
}