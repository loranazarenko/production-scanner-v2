// const API_BASE_URL = "http://localhost:8000";
const API_BASE_URL = "http://192.168.10.222:8000";

let scanner = null;
let scanning = false;

const scanButton = document.getElementById("scanButton");
const stopButton = document.getElementById("stopButton");
const reader = document.getElementById("reader");
const statusEl = document.getElementById("status");
const decodedValueEl = document.getElementById("decodedValue");
const lastOperationEl = document.getElementById("lastOperation");

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = "status";
  if (type) statusEl.classList.add(type);
}

function setDecodedValue(value) {
  decodedValueEl.textContent = value || "—";
}

function setLastOperation(text) {
  lastOperationEl.textContent = text || "—";
}

async function notifyBackend(barcode) {
  const response = await fetch(`${API_BASE_URL}/api/barcodes/${encodeURIComponent(barcode)}`);
  if (!response.ok) throw new Error(`Backend error: ${response.status}`);
  return await response.json();
}

async function stopScanner() {
  if (scanner && scanning) {
    try {
      await scanner.stop();
      await scanner.clear();
    } catch (error) {
      console.warn("Stop scanner warning:", error);
    }
  }
  scanning = false;
  reader.hidden = true;
  stopButton.hidden = true;
  scanButton.disabled = false;
  scanButton.textContent = "Сканировать снова";
}

async function onScanSuccess(decodedText) {
  if (!scanning) return;

  setDecodedValue(decodedText);
  setStatus(`Штрих-код распознан: ${decodedText}`, "success");
  setLastOperation("Загрузка данных из API...");

  await stopScanner();

  try {
    const backendData = await notifyBackend(decodedText);
    if (backendData && backendData.available_operations?.length) {
      const lastOp = backendData.last_operation;
      const opsList = backendData.available_operations.map(op => op.name).join(", ");
      setStatus(
        `Штрих-код распознан: ${decodedText}. Доступные операции: ${opsList}.`,
        "success"
      );
      if (lastOp) {
        setLastOperation(`${lastOp.operation_code} / ${lastOp.operation_name} от ${lastOp.performed_at}`);
      } else {
        setLastOperation("Операций по этому номеру еще нет.");
      }
    }
  } catch (error) {
    console.error(error);
    setStatus(`Ошибка при обращении к API: ${error}`, "error");
    setLastOperation("—");
  }
}

function isCameraSupported() {
    const md = navigator.mediaDevices;
    return !!(md && md.getUserMedia);
}

async function startScanner() {
    if (!isCameraSupported()) {
        setStatus(
            "Камера недоступна в этом браузере. Попробуйте Chrome на Android и откройте страницу по HTTPS.",
            "error"
        );
        return;
    }

  if (scanning) return;

  scanButton.disabled = true;
  scanButton.textContent = "Запуск камеры...";
  reader.hidden = false;
  stopButton.hidden = false;
  setStatus("Запрашиваем разрешение на использование камеры...");
  setDecodedValue("—");
  setLastOperation("—");

  scanner = new Html5Qrcode("reader");

  try {
    await scanner.start(
      { facingMode: "environment" },
      {
        fps: 10,
        qrbox: (viewfinderWidth, viewfinderHeight) => {
          const minEdge = Math.min(viewfinderWidth, viewfinderHeight);
          const boxWidth = Math.floor(minEdge * 0.8);
          return { width: boxWidth, height: Math.floor(boxWidth * 0.5) };
        },
        formatsToSupport: [
          Html5QrcodeSupportedFormats.CODE_128,
          Html5QrcodeSupportedFormats.CODE_39,
          Html5QrcodeSupportedFormats.EAN_13,
          Html5QrcodeSupportedFormats.EAN_8,
          Html5QrcodeSupportedFormats.UPC_A,
          Html5QrcodeSupportedFormats.UPC_E,
          Html5QrcodeSupportedFormats.QR_CODE
        ]
      },
      onScanSuccess,
      () => {}
    );

    scanning = true;
    scanButton.textContent = "Сканирование запущено";
    setStatus("Камера включена. Наведите телефон на штрих-код.");
  } catch (error) {
    console.error(error);
    setStatus(`Не удалось включить камеру: ${error}`, "error");
    reader.hidden = true;
    stopButton.hidden = true;
    scanButton.disabled = false;
    scanButton.textContent = "Сканировать";
  }
}

scanButton.addEventListener("click", startScanner);
stopButton.addEventListener("click", async () => {
  await stopScanner();
  setStatus("Сканирование остановлено.");
});
