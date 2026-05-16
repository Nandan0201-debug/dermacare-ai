import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowLeft,
  Bot,
  Camera,
  CheckCircle2,
  ClipboardCopy,
  Download,
  FileText,
  ImagePlus,
  Loader2,
  MessageCircle,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  UploadCloud,
  User,
} from "lucide-react";
import jsPDF from "jspdf";
import "./App.css";

function App() {
  const [view, setView] = useState("home");
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [userQuestion, setUserQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Upload and analyze an image first. After the report is generated, ask me follow-up questions here.",
    },
  ]);

  const chatMessagesRef = useRef(null);

  useEffect(() => {
    const chatMessages = chatMessagesRef.current;
    if (!chatMessages) return;

    chatMessages.scrollTo({
      top: chatMessages.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const handleImage = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setImage(file);
    setPreview(URL.createObjectURL(file));
    setReport(null);

    setMessages([
      {
        sender: "bot",
        text: "Image received. Click Analyze Image to generate your AI triage report.",
      },
    ]);
  };

  const analyzeImage = async () => {
    if (!image) {
      alert("Please upload or capture an image first.");
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("file", image);

    try {
      const response = await fetch("https://dermacare-ai-8g05.onrender.com/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Image analysis failed.");
      }

      const data = await response.json();
      setReport(data);

      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: "Report generated successfully. You can download the PDF or ask questions about the result.",
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `Analysis failed: ${error.message}`,
        },
      ]);
    }

    setLoading(false);
  };

  const getReportText = () => {
    if (!report) return "";

    const cleanValue = (value, fallback = "Not provided") => {
      if (value === null || value === undefined) return fallback;

      const text = String(value)
        .replace(/\*\*/g, "")
        .replace(/\u26A0\uFE0F?/g, "")
        .replace(/[\u2713\u2022]/g, "")
        .replace(/[–—]/g, "-")
        .replace(/→/g, "->")
        .split("")
        .filter((char) => {
          const code = char.charCodeAt(0);
          return code === 9 || code === 10 || code === 13 || (code >= 32 && code <= 126);
        })
        .join("")
        .replace(/[ \t]+\n/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();

      if (!text || /^(unknown|undefined|null|nan)$/i.test(text)) {
        return fallback;
      }

      return text;
    };

    const topPredictions = report.top_3_predictions
      ? report.top_3_predictions
          .map(
            (item, index) =>
              `${index + 1}. ${cleanValue(item.condition)} - ${cleanValue(
                item.confidence
              )}%`
          )
          .join("\n")
      : "Not available";

    return `
DermaCare AI Medical Triage Report

Generated On:
${new Date().toLocaleString()}

Possible Condition:
${cleanValue(report.possible_condition)}

Confidence:
${cleanValue(report.confidence)}

Risk Level:
${cleanValue(report.risk_level)}

Top 3 Predictions:
${topPredictions}

Emergency Warning:
${cleanValue(report.emergency_warning, "Monitor the condition and seek medical help if symptoms worsen.")}

AI Generated Report:
${cleanValue(report.ai_report)}

Disclaimer:
${cleanValue(report.disclaimer)}
`;
  };

  const downloadPDF = () => {
    if (!report) {
      alert("Please generate a report first.");
      return;
    }

    const doc = new jsPDF({ unit: "mm", format: "a4" });
    const margin = 16;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const contentWidth = pageWidth - margin * 2;
    const footerTop = pageHeight - 28;
    const generatedAt = new Date().toLocaleString();

    const colors = {
      navy: [7, 26, 51],
      blue: [22, 135, 255],
      cyan: [34, 211, 238],
      text: [15, 23, 42],
      muted: [90, 105, 124],
      border: [214, 224, 236],
      soft: [243, 248, 252],
      warning: [180, 83, 9],
    };

    const cleanValue = (value, fallback = "Not provided") => {
      if (value === null || value === undefined) return fallback;

      const text = String(value)
        .replace(/\*\*/g, "")
        .replace(/\u26A0\uFE0F?/g, "")
        .replace(/[\u2713\u2022]/g, "")
        .replace(/[–—]/g, "-")
        .replace(/→/g, "->")
        .split("")
        .filter((char) => {
          const code = char.charCodeAt(0);
          return code === 9 || code === 10 || code === 13 || (code >= 32 && code <= 126);
        })
        .join("")
        .replace(/[ \t]+\n/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();

      if (!text || /^(unknown|undefined|null|nan)$/i.test(text)) {
        return fallback;
      }

      return text;
    };

    const formatConfidence = (value) => {
      const clean = cleanValue(value);
      if (clean === "Not provided") return clean;
      return clean.includes("%") ? clean : `${clean}%`;
    };

    const condition = cleanValue(report.possible_condition);
    const confidence = formatConfidence(report.confidence);
    const riskLevel = cleanValue(report.risk_level);
    const emergencyWarning = cleanValue(
      report.emergency_warning,
      "No immediate emergency flag was returned. Continue monitoring and seek medical care if symptoms worsen."
    );
    const aiReport = cleanValue(
      report.ai_report,
      "No narrative report was returned by the analysis service."
    );
    const disclaimer = cleanValue(
      report.disclaimer,
      "This report is a preliminary AI-assisted triage aid only. It is not a medical diagnosis and does not replace evaluation by a licensed healthcare professional."
    );
    const predictions = Array.isArray(report.top_3_predictions)
      ? report.top_3_predictions.slice(0, 3)
      : [];

    let y = 0;

    const addHeader = () => {
      doc.setFillColor(...colors.navy);
      doc.rect(0, 0, pageWidth, 38, "F");

      doc.setFillColor(...colors.blue);
      doc.roundedRect(margin, 10, 18, 18, 4, 4, "F");
      doc.setTextColor(255, 255, 255);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(12);
      doc.text("DC", margin + 9, 21.5, { align: "center" });

      doc.setFontSize(18);
      doc.text("DermaCare AI", margin + 24, 17);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      doc.setTextColor(205, 220, 235);
      doc.text("AI-Assisted Skin & Wound Triage Report", margin + 24, 24);

      doc.setFontSize(8.5);
      doc.text(`Generated: ${generatedAt}`, pageWidth - margin, 16, {
        align: "right",
      });
      doc.text("Preliminary Assessment", pageWidth - margin, 23, {
        align: "right",
      });

      y = 50;
    };

    const addFooter = () => {
      const pageNumber = doc.internal.getNumberOfPages();

      doc.setDrawColor(...colors.border);
      doc.line(margin, footerTop, pageWidth - margin, footerTop);

      doc.setTextColor(...colors.navy);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8.5);
      doc.text("DermaCare AI", margin, pageHeight - 21);

      doc.setTextColor(...colors.muted);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7.5);
      doc.text(
        "Email: nandanpalla400@gmail.com",
        margin,
        pageHeight - 16
      );
      doc.text(
        "GitHub: github.com/Nandan0201-debug",
        margin,
        pageHeight - 11
      );
      doc.text(
        "LinkedIn: linkedin.com/in/palla-jothisk-nandan",
        margin + 66,
        pageHeight - 11
      );

      doc.setFont("helvetica", "bold");
      doc.setTextColor(...colors.warning);
      doc.text(
        "Preliminary AI guidance only - not a medical diagnosis.",
        pageWidth - margin,
        pageHeight - 16,
        { align: "right" }
      );
      doc.text(`Page ${pageNumber}`, pageWidth - margin, pageHeight - 10, {
        align: "right",
      });
    };

    const ensureSpace = (height) => {
      if (y + height <= footerTop - 6) return;

      addFooter();
      doc.addPage();
      addHeader();
    };

    const sectionTitle = (title) => {
      ensureSpace(14);
      doc.setTextColor(...colors.navy);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(11);
      doc.text(title.toUpperCase(), margin, y);
      doc.setDrawColor(...colors.cyan);
      doc.setLineWidth(0.5);
      doc.line(margin, y + 3, pageWidth - margin, y + 3);
      y += 10;
    };

    const drawSummaryCard = (x, width, label, value) => {
      doc.setFillColor(...colors.soft);
      doc.setDrawColor(...colors.border);
      doc.roundedRect(x, y, width, 32, 3, 3, "FD");

      doc.setFont("helvetica", "bold");
      doc.setFontSize(7.5);
      doc.setTextColor(...colors.blue);
      doc.text(label.toUpperCase(), x + 5, y + 8);

      doc.setFontSize(10.5);
      doc.setTextColor(...colors.text);
      const lines = doc.splitTextToSize(value, width - 10).slice(0, 3);
      doc.text(lines, x + 5, y + 17);
    };

    const drawTextBlock = (title, text, options = {}) => {
      const fill = options.warning ? [255, 247, 237] : [255, 255, 255];
      const border = options.warning ? [251, 191, 36] : colors.border;
      const textColor = options.warning ? colors.warning : colors.text;
      const lines = doc.splitTextToSize(text, contentWidth - 12);
      const lineHeight = 5;
      let remainingLines = [...lines];
      let currentTitle = title;

      while (remainingLines.length) {
        const availableHeight = footerTop - y - 18;
        if (availableHeight < 20) {
          ensureSpace(40);
        }

        const maxLines = Math.max(1, Math.floor((footerTop - y - 24) / lineHeight));
        const pageLines = remainingLines.slice(0, maxLines);
        remainingLines = remainingLines.slice(maxLines);
        const blockHeight = Math.max(24, pageLines.length * lineHeight + 17);

        ensureSpace(blockHeight + 8);

        doc.setFillColor(...fill);
        doc.setDrawColor(...border);
        doc.roundedRect(margin, y, contentWidth, blockHeight, 3, 3, "FD");

        doc.setFont("helvetica", "bold");
        doc.setFontSize(9);
        doc.setTextColor(...colors.navy);
        doc.text(currentTitle, margin + 6, y + 8);

        doc.setFont("helvetica", "normal");
        doc.setFontSize(9.5);
        doc.setTextColor(...textColor);
        doc.text(pageLines, margin + 6, y + 16);

        y += blockHeight + 8;
        currentTitle = `${title} (continued)`;
      }
    };

    addHeader();

    sectionTitle("Assessment Summary");
    const cardGap = 5;
    const cardWidth = (contentWidth - cardGap * 2) / 3;
    drawSummaryCard(margin, cardWidth, "Possible Condition", condition);
    drawSummaryCard(
      margin + cardWidth + cardGap,
      cardWidth,
      "Confidence",
      confidence
    );
    drawSummaryCard(
      margin + (cardWidth + cardGap) * 2,
      cardWidth,
      "Risk Level",
      riskLevel
    );
    y += 42;

    sectionTitle("Top Model Predictions");
    if (predictions.length) {
      const rowHeight = 12;
      ensureSpace(rowHeight * predictions.length + 12);
      doc.setFillColor(...colors.navy);
      doc.roundedRect(margin, y, contentWidth, 10, 2, 2, "F");
      doc.setTextColor(255, 255, 255);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8);
      doc.text("RANK", margin + 5, y + 6.5);
      doc.text("PREDICTED CONDITION", margin + 26, y + 6.5);
      doc.text("CONFIDENCE", pageWidth - margin - 5, y + 6.5, {
        align: "right",
      });
      y += 10;

      predictions.forEach((item, index) => {
        doc.setFillColor(index % 2 === 0 ? 248 : 255, 250, 252);
        doc.rect(margin, y, contentWidth, rowHeight, "F");
        doc.setTextColor(...colors.text);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);
        doc.text(String(index + 1), margin + 6, y + 7.8);
        doc.text(
          doc
            .splitTextToSize(cleanValue(item.condition), contentWidth - 78)
            .slice(0, 1),
          margin + 26,
          y + 7.8
        );
        doc.text(
          formatConfidence(item.confidence),
          pageWidth - margin - 5,
          y + 7.8,
          { align: "right" }
        );
        y += rowHeight;
      });
      y += 8;
    } else {
      drawTextBlock("Predictions", "No top prediction list was returned.");
    }

    sectionTitle("Clinical Guidance");
    drawTextBlock("Emergency / Urgency Guidance", emergencyWarning, {
      warning: /urgent|emergency|immediate|risk/i.test(emergencyWarning),
    });
    drawTextBlock("AI-Generated Triage Notes", aiReport);

    sectionTitle("Important Disclaimer");
    drawTextBlock("Medical Disclaimer", disclaimer, { warning: true });

    addFooter();

    doc.save("dermacare-ai-medical-report.pdf");
  };

  const copyReport = async () => {
    if (!report) {
      alert("Please generate a report first.");
      return;
    }

    await navigator.clipboard.writeText(getReportText());
    alert("Report copied.");
  };

  const clearResult = () => {
    setImage(null);
    setPreview(null);
    setReport(null);
    setMessages([
      {
        sender: "bot",
        text: "Result cleared. Upload a new image to begin again.",
      },
    ]);
  };

  const clearChat = () => {
    setMessages([
      {
        sender: "bot",
        text: report
          ? "Chat cleared. Ask me anything about your generated report."
          : "Chat cleared. Upload and analyze an image first.",
      },
    ]);
  };

  const scrollToHomeSection = (event, sectionId) => {
    event.preventDefault();
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  const sendQuestion = async () => {
    if (!userQuestion.trim()) return;

    const question = userQuestion;
    setUserQuestion("");
    setChatLoading(true);

    setMessages((prev) => [
      ...prev,
      { sender: "user", text: question },
      { sender: "bot", text: "Thinking..." },
    ]);

    try {
      const response = await fetch("https://dermacare-ai-8g05.onrender.com/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          context: report ? getReportText() : "No report generated yet.",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Chat failed.");
      }

      const data = await response.json();

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          sender: "bot",
          text: data.answer,
        };
        return updated;
      });
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          sender: "bot",
          text: `Chat failed: ${error.message}`,
        };
        return updated;
      });
    }

    setChatLoading(false);
  };

  const formatMessage = (text) => {
    return text.split("\n").map((line, index) => {
      const clean = line.replace(/\*\*/g, "").trim();

      if (!clean) return <br key={index} />;

      if (/^\d+\./.test(clean)) {
        return (
          <p key={index} className="number-line">
            {clean}
          </p>
        );
      }

      if (
        clean.startsWith("-") ||
        clean.startsWith("•") ||
        clean.startsWith("✓")
      ) {
        return (
          <p key={index} className="bullet-line">
            {clean}
          </p>
        );
      }

      return <p key={index}>{clean}</p>;
    });
  };

  if (view === "home") {
    return (
      <div className="home-page">
        <nav className="home-nav">
          <div className="logo">
            <div className="logo-icon">
              <ShieldCheck size={26} />
            </div>
            <span>DermaCare AI</span>
          </div>

          <div className="nav-menu">
            <a href="#how" onClick={(event) => scrollToHomeSection(event, "how")}>
              How it Works
            </a>
            <a
              href="#features"
              onClick={(event) => scrollToHomeSection(event, "features")}
            >
              Features
            </a>
            <a
              href="#safety"
              onClick={(event) => scrollToHomeSection(event, "safety")}
            >
              Safety
            </a>
            <button onClick={() => setView("analyze")}>Analyze Wound</button>
          </div>
        </nav>

        <section className="hero-section">
          <div className="hero-left">
            <div className="hero-badge">
              <Sparkles size={16} />
              AI Wound Analysis
            </div>

            <h1>Objective wound assessment with AI precision</h1>

            <p>
              Upload skin or wound photos and receive a preliminary AI-assisted
              triage report with risk guidance, PDF export, and chatbot support.
            </p>

            <button className="hero-button" onClick={() => setView("analyze")}>
              Analyze Wound
            </button>
          </div>

          <div className="hero-right">
            <div className="hero-visual-card">
              <div className="visual-top">
                <div className="pulse-icon">
                  <Activity size={42} />
                </div>
                <div>
                  <h3>Clinical-style AI workflow</h3>
                  <p>Image analysis → triage report → PDF → chatbot guidance</p>
                </div>
              </div>

              <div className="visual-grid">
                <div>
                  <span>Condition</span>
                  <strong>Skin/Wound Screening</strong>
                </div>
                <div>
                  <span>Output</span>
                  <strong>PDF Medical Report</strong>
                </div>
                <div>
                  <span>Assistant</span>
                  <strong>Follow-up Chatbot</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="info-section" id="how">
          <div className="section-heading">
            <span>How it Works</span>
            <h2>Simple AI-powered medical triage workflow</h2>
          </div>

          <div className="feature-grid">
            <div className="feature-card">
              <Camera />
              <h3>Upload Image</h3>
              <p>Capture or upload a wound, rash, acne, burn, or skin image.</p>
            </div>

            <div className="feature-card">
              <Activity />
              <h3>AI Vision Analysis</h3>
              <p>CLIP-based AI model screens the image and predicts possible conditions.</p>
            </div>

            <div className="feature-card">
              <FileText />
              <h3>Medical Report</h3>
              <p>Generate a structured triage report with confidence and risk level.</p>
            </div>

            <div className="feature-card">
              <MessageCircle />
              <h3>Chat Assistant</h3>
              <p>Ask safe follow-up questions about the generated report.</p>
            </div>
          </div>
        </section>

        <section className="workflow-section" id="features">
          <div className="section-heading">
            <span>Features</span>
            <h2>From photo to PDF in four steps</h2>
          </div>

          <div className="workflow-row">
            <div>
              <span>01</span>
              <h3>Upload</h3>
              <p>Select or capture a skin/wound image.</p>
            </div>
            <div>
              <span>02</span>
              <h3>Analyze</h3>
              <p>Run the image through the AI model.</p>
            </div>
            <div>
              <span>03</span>
              <h3>Download</h3>
              <p>Export the generated medical report as PDF.</p>
            </div>
            <div>
              <span>04</span>
              <h3>Ask</h3>
              <p>Use the chatbot for safe follow-up guidance.</p>
            </div>
          </div>
        </section>

        <section className="safety-section" id="safety">
          <div className="section-heading">
            <span>Safety</span>
            <h2>Built for safe preliminary guidance</h2>
          </div>

          <div className="safety-grid">
            <div>
              <h3>Not a diagnosis</h3>
              <p>This system gives preliminary AI-assisted triage only.</p>
            </div>
            <div>
              <h3>No prescriptions</h3>
              <p>The chatbot does not prescribe medicines or dosages.</p>
            </div>
            <div>
              <h3>Doctor-first guidance</h3>
              <p>Serious symptoms are redirected to professional care.</p>
            </div>
          </div>
        </section>

        <footer className="contact-section">
          <div>
            <h2>DermaCare AI</h2>
            <p>AI-assisted skin and wound triage portfolio project.</p>
          </div>
          <div>
            <p>Email: nandanpalla400@gmail.com</p>
            <p>GitHub: github.com/Nandan0201-debug</p>
            <p>LinkedIn: linkedin.com/in/palla-jothisk-nandan</p>
          </div>
        </footer>
      </div>
    );
  }

  return (
    <div className="analyze-page">
      <nav className="analyze-nav">
        <button onClick={() => setView("home")} className="back-home">
          <ArrowLeft size={18} />
          Back to Home
        </button>

        <div className="analysis-title">
          <ShieldCheck size={24} />
          <span>DermaCare AI Analysis</span>
        </div>
      </nav>

      <div className="analyze-layout">
        <main className="analysis-main">
          <section className="analysis-hero">
            <div>
              <div className="hero-badge">
                <Sparkles size={16} />
                AI Skin & Wound Analysis
              </div>
              <h1>Analyze image and generate PDF report</h1>
              <p>
                Upload an image, preview it, analyze the wound or skin condition,
                and download the generated triage report as PDF.
              </p>
            </div>
          </section>

          <section className="steps-bar">
            <div><span>1</span>Upload Image</div>
            <div><span>2</span>Preview Image</div>
            <div><span>3</span>Click Analyze</div>
            <div><span>4</span>Download PDF</div>
          </section>

          <section className="upload-preview-section">
            <label className="upload-box">
              <UploadCloud size={48} />
              <h3>Upload or Capture Image</h3>
              <p>JPEG, PNG, WebP, GIF • Max 8MB</p>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleImage}
              />
            </label>

            <div className="preview-box">
              {preview ? (
                <>
                  <img src={preview} alt="Uploaded preview" />
                  <button
                    className="analyze-button"
                    onClick={analyzeImage}
                    disabled={loading}
                  >
                    {loading ? <Loader2 className="spin" size={18} /> : <Camera size={18} />}
                    {loading ? "Analyzing..." : "Analyze Image"}
                  </button>
                </>
              ) : (
                <div className="empty-preview">
                  <ImagePlus size={46} />
                  <p>Image preview will appear here</p>
                </div>
              )}
            </div>
          </section>

          <section className={`pdf-card ${report ? "pdf-ready" : ""}`}>
            <div className="pdf-header">
              <div>
                <span>PDF Report</span>
                <h2>
                  {report
                    ? "PDF report generated successfully"
                    : "PDF report will appear after analysis"}
                </h2>
              </div>
              {report && <CheckCircle2 size={28} />}
            </div>

            {report ? (
              <>
                <div className="pdf-summary">
                  <div>
                    <span>Condition</span>
                    <strong>{report.possible_condition}</strong>
                  </div>
                  <div>
                    <span>Confidence</span>
                    <strong>{report.confidence}</strong>
                  </div>
                  <div>
                    <span>Risk Level</span>
                    <strong>{report.risk_level}</strong>
                  </div>
                </div>

                <p>
                  Your full AI-generated medical triage report is ready. The full
                  report is included inside the PDF download.
                </p>

                <div className="pdf-actions">
                  <button onClick={downloadPDF}>
                    <Download size={18} />
                    Download PDF
                  </button>

                  <button className="secondary-action" onClick={copyReport}>
                    <ClipboardCopy size={18} />
                    Copy Report
                  </button>

                  <button className="danger-action" onClick={clearResult}>
                    <Trash2 size={18} />
                    Clear Result
                  </button>
                </div>
              </>
            ) : (
              <p>
                After you click Analyze Image, the PDF download option will be
                available here.
              </p>
            )}
          </section>
        </main>

        <aside className="chatbot-panel">
          <div className="chatbot-header">
            <div>
              <Bot size={22} />
              <strong>DermaCare Assistant</strong>
            </div>

            <button onClick={clearChat}>
              <Trash2 size={17} />
            </button>
          </div>

          <div className="chatbot-messages" ref={chatMessagesRef}>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`message ${
                  msg.sender === "user" ? "user-message" : "bot-message"
                }`}
              >
                <div className="avatar">
                  {msg.sender === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="message-bubble">{formatMessage(msg.text)}</div>
              </div>
            ))}
          </div>

          <div className="chatbot-input">
            <input
              value={userQuestion}
              placeholder="Ask about your report..."
              onChange={(e) => setUserQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendQuestion()}
              disabled={chatLoading}
            />

            <button onClick={sendQuestion} disabled={chatLoading}>
              {chatLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;
