const API_HEALTH_URL = "http://localhost:8000/health";
const CHECK_INTERVAL_MS = 30000; // Poll every 30 seconds

/**
 * Dynamically draws a colored status icon using ImageData.
 * @param {string} colorHex Hex color code for the icon background.
 */
function createStatusIconImageData(colorHex) {
  const canvasSize = 32;
  const canvas = new OffscreenCanvas(canvasSize, canvasSize);
  const ctx = canvas.getContext("2d");

  // Draw background circle
  ctx.beginPath();
  ctx.arc(16, 16, 14, 0, 2 * Math.PI);
  ctx.fillStyle = colorHex;
  ctx.fill();

  // Draw a clean document icon in the center (white)
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(11, 8, 10, 16); // Base page
  ctx.fillStyle = colorHex;
  ctx.fillRect(13, 11, 6, 2);  // Line 1
  ctx.fillRect(13, 15, 6, 2);  // Line 2
  ctx.fillRect(13, 19, 4, 2);  // Line 3

  return ctx.getImageData(0, 0, canvasSize, canvasSize);
}

/**
 * Checks FastAPI server health and changes icon background color.
 */
async function checkHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000); // 2-second timeout

    const response = await fetch(API_HEALTH_URL, {
      method: "GET",
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      // Server is active -> Green Icon
      setIconColor("#10B981");
    } else {
      // Server error -> Gray Icon
      setIconColor("#6B7280");
    }
  } catch (error) {
    // Server offline -> Gray Icon
    setIconColor("#6B7280");
  }
}

/**
 * Updates the Chrome extension action icon and clears any text badges.
 */
function setIconColor(hexColor) {
  // Clear old text badge if it exists
  chrome.action.setBadgeText({ text: "" });

  // Generate dynamic icon image
  const imageData = createStatusIconImageData(hexColor);
  chrome.action.setIcon({ imageData: imageData });
}

// Perform initial check on Service Worker startup
checkHealth();

// Set up polling loop every 30 seconds
setInterval(checkHealth, CHECK_INTERVAL_MS);