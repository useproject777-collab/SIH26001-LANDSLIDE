import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import MapView from "./MapView";
import { API_BASE, apiGet, apiPost } from "./api";
import "./App.css";

const DEFAULT_LOCATION_ID = 1;
const REFRESH_MS = 5 * 60 * 1000;

const I18N = {
  en: { title: "NER Landslide Early Warning System", subtitle: "Live rainfall, terrain intelligence, alerts and risk monitoring", search: "Search city, district or monitoring point...", searchBtn: "Search", myLocation: "Use My Location", manual: "Manual Location", calculate: "Calculate this location", alerts: "Enable Alerts", enabled: "Alerts Enabled", logout: "Logout", focus: "Current Monitoring Focus", risk: "Risk Status", history: "Risk History", activeAlerts: "Active Alerts", report: "Geo-tagged Citizen Report" },
  ta: { title: "வடகிழக்கு நிலச்சரிவு முன் எச்சரிக்கை அமைப்பு", subtitle: "நேரடி மழைப்பொழிவு, நில அமைப்பு, எச்சரிக்கைகள் மற்றும் அபாய கண்காணிப்பு", search: "நகரம், மாவட்டம் அல்லது கண்காணிப்பு இடத்தை தேடுங்கள்...", searchBtn: "தேடு", myLocation: "என் இருப்பிடத்தைப் பயன்படுத்து", manual: "கைமுறை இருப்பிடம்", calculate: "இந்த இடத்தை கணக்கிடு", alerts: "எச்சரிக்கைகளை இயக்கு", enabled: "எச்சரிக்கைகள் இயங்குகின்றன", logout: "வெளியேறு", focus: "தற்போதைய கண்காணிப்பு இடம்", risk: "அபாய நிலை", history: "அபாய வரலாறு", activeAlerts: "செயலில் உள்ள எச்சரிக்கைகள்", report: "புவியியல் குறியீட்டுடன் தகவல்" },
  hi: { title: "पूर्वोत्तर भूस्खलन पूर्व चेतावनी प्रणाली", subtitle: "लाइव वर्षा, भू-भाग, चेतावनी और जोखिम निगरानी", search: "शहर, जिला या निगरानी स्थान खोजें...", searchBtn: "खोजें", myLocation: "मेरी लोकेशन", manual: "मैनुअल लोकेशन", calculate: "इस स्थान की गणना करें", alerts: "अलर्ट सक्षम करें", enabled: "अलर्ट सक्षम", logout: "लॉग आउट", focus: "वर्तमान निगरानी स्थान", risk: "जोखिम स्थिति", history: "जोखिम इतिहास", activeAlerts: "सक्रिय अलर्ट", report: "जियो-टैग फील्ड रिपोर्ट" },
  te: { title: "ఈశాన్య భూస्खలనం ముందస్తు హెచ్చరిక వ్యవస్థ", subtitle: "ప్రత్యక్ష వర్షపాతం, భూభాగం, హెచ్చరికలు మరియు ప్రమాద పర్యవేక్షణ", search: "నగరం లేదా పర్యవేక్షణ స్థలాన్ని శోధించండి...", searchBtn: "శోధించు", myLocation: "నా స్థానాన్ని ఉపయోగించు", manual: "మాన్యువల్ స్థానం", calculate: "ఈ స్థానాన్ని లెక్కించు", alerts: "హెచ్చరికలను ప్రారంభించు", enabled: "హెచ్చరికలు ప్రారంభించబడ్డాయి", logout: "లాగ్ అవుట్", focus: "ప్రస్తుత పర్యవేక్షణ స్థానం", risk: "ప్రమాద స్థితి", history: "ప్రమాద చరిత్ర", activeAlerts: "క్రియాశీల హెచ్చరికలు", report: "జియో-ట్యాగ్ నివేదిక" },
  kn: { title: "ಈಶಾನ್ಯ ಭೂಕುಸಿತ ಮುನ್ನೆಚ್ಚರಿಕೆ ವ್ಯವಸ್ಥೆ", subtitle: "ನೇರ ಮಳೆ, ಭೂಪ್ರದೇಶ, ಎಚ್ಚರಿಕೆಗಳು ಮತ್ತು ಅಪಾಯ ಮೇಲ್ವಿಚಾರಣೆ", search: "ನಗರ ಅಥವಾ ಮೇಲ್ವಿಚಾರಣಾ ಸ್ಥಳವನ್ನು ಹುಡುಕಿ...", searchBtn: "ಹುಡುಕಿ", myLocation: "ನನ್ನ ಸ್ಥಳ ಬಳಸಿ", manual: "ಹಸ್ತಚಾಲಿತ ಸ್ಥಳ", calculate: "ಈ ಸ್ಥಳವನ್ನು ಲೆಕ್ಕಿಸಿ", alerts: "ಎಚ್ಚರಿಕೆಗಳನ್ನು ಸಕ್ರಿಯಗೊಳಿಸಿ", enabled: "ಎಚ್ಚರಿಕೆಗಳು ಸಕ್ರಿಯ", logout: "ಲಾಗ್ ಔಟ್", focus: "ಪ್ರಸ್ತುತ ಮೇಲ್ವಿಚಾರಣಾ ಸ್ಥಳ", risk: "ಅಪಾಯ ಸ್ಥಿತಿ", history: "ಅಪಾಯ ಇತಿಹಾಸ", activeAlerts: "ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು", report: "ಜಿಯೋ-ಟ್ಯಾಗ್ ವರದಿ" },
  ml: { title: "വടക്കുകിഴക്കൻ മണ്ണിടിച്ചിൽ മുൻകരുതൽ സംവിധാനം", subtitle: "തത്സമയ മഴ, ഭൂപ്രകൃതി, മുന്നറിയിപ്പുകൾ, അപകട നിരീക്ഷണം", search: "നഗരം അല്ലെങ്കിൽ നിരീക്ഷണ സ്ഥലം തിരയുക...", searchBtn: "തിരയുക", myLocation: "എന്റെ സ്ഥലം ഉപയോഗിക്കുക", manual: "മാനുവൽ സ്ഥലം", calculate: "ഈ സ്ഥലം കണക്കാക്കുക", alerts: "അലേർട്ടുകൾ പ്രവർത്തിപ്പിക്കുക", enabled: "അലേർട്ടുകൾ പ്രവർത്തിക്കുന്നു", logout: "ലോഗ് ഔട്ട്", focus: "നിലവിലെ നിരീക്ഷണ സ്ഥലം", risk: "അപകട നില", history: "അപകട ചരിത്രം", activeAlerts: "സജീവ അലേർട്ടുകൾ", report: "ജിയോ-ടാഗ് റിപ്പോർട്ട്" },
  bn: { title: "উত্তর-পূর্ব ভূমিধস আগাম সতর্কতা ব্যবস্থা", subtitle: "লাইভ বৃষ্টি, ভূখণ্ড, সতর্কতা ও ঝুঁকি পর্যবেক্ষণ", search: "শহর বা পর্যবেক্ষণ স্থান খুঁজুন...", searchBtn: "খুঁজুন", myLocation: "আমার অবস্থান ব্যবহার করুন", manual: "ম্যানুয়াল অবস্থান", calculate: "এই অবস্থান হিসাব করুন", alerts: "সতর্কতা চালু করুন", enabled: "সতর্কতা চালু", logout: "লগ আউট", focus: "বর্তমান পর্যবেক্ষণ স্থান", risk: "ঝুঁকির অবস্থা", history: "ঝুঁকির ইতিহাস", activeAlerts: "সক্রিয় সতর্কতা", report: "জিও-ট্যাগ রিপোর্ট" },
  mr: { title: "ईशान्य भूस्खलन पूर्वसूचना प्रणाली", subtitle: "थेट पाऊस, भूभाग, सूचना आणि जोखीम निरीक्षण", search: "शहर किंवा निरीक्षण स्थान शोधा...", searchBtn: "शोधा", myLocation: "माझे स्थान वापरा", manual: "मॅन्युअल स्थान", calculate: "या स्थानाची गणना करा", alerts: "सूचना सुरू करा", enabled: "सूचना सुरू", logout: "लॉग आउट", focus: "सध्याचे निरीक्षण स्थान", risk: "जोखीम स्थिती", history: "जोखीम इतिहास", activeAlerts: "सक्रिय सूचना", report: "जिओ-टॅग अहवाल" },
  gu: { title: "ઉત્તરપૂર્વ ભૂસ્ખલન પૂર્વ ચેતવણી પ્રણાલી", subtitle: "લાઇવ વરસાદ, ભૂપ્રદેશ, ચેતવણીઓ અને જોખમ નિરીક્ષણ", search: "શહેર અથવા મોનિટરિંગ સ્થાન શોધો...", searchBtn: "શોધો", myLocation: "મારું સ્થાન વાપરો", manual: "મેન્યુઅલ સ્થાન", calculate: "આ સ્થાનની ગણતરી કરો", alerts: "ચેતવણીઓ સક્ષમ કરો", enabled: "ચેતવણીઓ સક્ષમ", logout: "લૉગ આઉટ", focus: "વર્તમાન મોનિટરિંગ સ્થાન", risk: "જોખમ સ્થિતિ", history: "જોખમ ઇતિહાસ", activeAlerts: "સક્રિય ચેતવણીઓ", report: "જિયો-ટેગ રિપોર્ટ" },
  pa: { title: "ਉੱਤਰ-ਪੂਰਬ ਭੂਸਖਲਨ ਪਹਿਲਾਂ ਚੇਤਾਵਨੀ ਪ੍ਰਣਾਲੀ", subtitle: "ਲਾਈਵ ਮੀਂਹ, ਭੂ-ਭਾਗ, ਚੇਤਾਵਨੀਆਂ ਅਤੇ ਜੋਖਮ ਨਿਗਰਾਨੀ", search: "ਸ਼ਹਿਰ ਜਾਂ ਨਿਗਰਾਨੀ ਸਥਾਨ ਖੋਜੋ...", searchBtn: "ਖੋਜੋ", myLocation: "ਮੇਰੀ ਸਥਿਤੀ ਵਰਤੋ", manual: "ਮੈਨੁਅਲ ਸਥਿਤੀ", calculate: "ਇਸ ਸਥਿਤੀ ਦੀ ਗਣਨਾ ਕਰੋ", alerts: "ਚੇਤਾਵਨੀਆਂ ਚਾਲੂ ਕਰੋ", enabled: "ਚੇਤਾਵਨੀਆਂ ਚਾਲੂ", logout: "ਲੌਗ ਆਉਟ", focus: "ਮੌਜੂਦਾ ਨਿਗਰਾਨੀ ਸਥਾਨ", risk: "ਜੋਖਮ ਸਥਿਤੀ", history: "ਜੋਖਮ ਇਤਿਹਾਸ", activeAlerts: "ਸਰਗਰਮ ਚੇਤਾਵਨੀਆਂ", report: "ਜਿਓ-ਟੈਗ ਰਿਪੋਰਟ" },
  or: { title: "ଉତ୍ତର-ପୂର୍ବ ଭୂସ୍ଖଳନ ପୂର୍ବ ସତର୍କତା ବ୍ୟବସ୍ଥା", subtitle: "ଲାଇଭ ବର୍ଷା, ଭୂଭାଗ, ସତର୍କତା ଓ ବିପଦ ନିରୀକ୍ଷଣ", search: "ସହର କିମ୍ବା ନିରୀକ୍ଷଣ ସ୍ଥାନ ଖୋଜନ୍ତୁ...", searchBtn: "ଖୋଜନ୍ତୁ", myLocation: "ମୋ ସ୍ଥାନ ବ୍ୟବହାର କରନ୍ତୁ", manual: "ମାନୁଆଲ ସ୍ଥାନ", calculate: "ଏହି ସ୍ଥାନ ଗଣନା କରନ୍ତୁ", alerts: "ସତର୍କତା ସକ୍ରିୟ କରନ୍ତୁ", enabled: "ସତର୍କତା ସକ୍ରିୟ", logout: "ଲଗ ଆଉଟ", focus: "ବର୍ତ୍ତମାନ ନିରୀକ୍ଷଣ ସ୍ଥାନ", risk: "ବିପଦ ସ୍ଥିତି", history: "ବିପଦ ଇତିହାସ", activeAlerts: "ସକ୍ରିୟ ସତର୍କତା", report: "ଜିଓ-ଟ୍ୟାଗ ରିପୋର୍ଟ" },
  as: { title: "উত্তৰ-পূব ভূমিস্খলন আগতীয়া সতৰ্কতা ব্যৱস্থা", subtitle: "লাইভ বৰষুণ, ভূখণ্ড, সতৰ্কতা আৰু বিপদ নিৰীক্ষণ", search: "চহৰ বা নিৰীক্ষণ স্থান বিচাৰক...", searchBtn: "বিচাৰক", myLocation: "মোৰ স্থান ব্যৱহাৰ কৰক", manual: "হস্তচালিত স্থান", calculate: "এই স্থান গণনা কৰক", alerts: "সতৰ্কতা সক্ৰিয় কৰক", enabled: "সতৰ্কতা সক্ৰিয়", logout: "লগ আউট", focus: "বৰ্তমান নিৰীক্ষণ স্থান", risk: "বিপদৰ অৱস্থা", history: "বিপদৰ ইতিহাস", activeAlerts: "সক্ৰিয় সতৰ্কতা", report: "জিঅ'-টেগ ৰিপ'ৰ্ট" },
  ur: { title: "شمال مشرق لینڈ سلائیڈ ابتدائی انتباہ نظام", subtitle: "براہ راست بارش، خطہ، انتباہات اور خطرے کی نگرانی", search: "شہر یا نگرانی کا مقام تلاش کریں...", searchBtn: "تلاش", myLocation: "میری موجودہ جگہ", manual: "دستی مقام", calculate: "اس مقام کا حساب کریں", alerts: "انتباہات فعال کریں", enabled: "انتباہات فعال", logout: "لاگ آؤٹ", focus: "موجودہ نگرانی کا مقام", risk: "خطرے کی حالت", history: "خطرے کی تاریخ", activeAlerts: "فعال انتباہات", report: "جیو ٹیگ رپورٹ" }
};

const RISK_COLORS = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#ef4444",
  CRITICAL: "#991b1b",
};

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  });
}

function riskClass(level = "LOW") {
  return `risk-pill risk-${level.toLowerCase()}`;
}

function Dashboard({ auth, onLogout }) {
  const [risk, setRisk] = useState(null);
  const [locations, setLocations] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [selectedCoordinate, setSelectedCoordinate] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [focusCoordinate, setFocusCoordinate] = useState(null);
  const [satelliteEnabled, setSatelliteEnabled] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [stateSummary, setStateSummary] = useState([]);
  const [modelStatus, setModelStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [terrainBusy, setTerrainBusy] = useState(false);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState(null);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [activeSource, setActiveSource] = useState("default");
  const [citizenReports, setCitizenReports] = useState([]);
  const [roadReports, setRoadReports] = useState([]);
  const [reportForm, setReportForm] = useState({ type: "OBSERVATION", description: "", reporter: auth?.name || "Citizen" });
  const [reportFile, setReportFile] = useState(null);
  const [roadForm, setRoadForm] = useState({ road: "", status: "BLOCKED", description: "", reporter: "Field Official" });
  const [language, setLanguage] = useState("en");
  const t = I18N[language] || I18N.en;
  const [manualLat, setManualLat] = useState(25.5);
  const [manualLon, setManualLon] = useState(92.5);

  const currentIsRaining =
    Number(risk?.current_rain_mm || 0) > 0 ||
    Number(risk?.rainfall_1h || 0) > 0;

  const refreshDefault = useCallback(async () => {
    const [live, hist] = await Promise.all([
      apiGet(`/api/live-risk/${DEFAULT_LOCATION_ID}`),
      apiGet(`/api/risk-history/${DEFAULT_LOCATION_ID}`),
    ]);
    setRisk(live);
    setHistory(hist.slice().reverse());
  }, []);

  const refreshGlobal = useCallback(async () => {
    const [all, summary, activeAlerts, status, states, roads] = await Promise.all([
      apiGet("/api/live-risk-all"),
      apiGet("/api/analytics/summary"),
      apiGet("/api/alerts?status=ACTIVE"),
      apiGet("/api/ml/status"),
      apiGet("/api/analytics/state-summary"),
      apiGet("/api/road-reports"),
    ]);
    setLocations(all);
    setAnalytics(summary);
    setAlerts(activeAlerts);
    setModelStatus(status);
    setStateSummary(states);
    setRoadReports(roads);
  }, []);

  const refreshEverything = useCallback(async () => {
    try {
      setError("");
      if (activeSource === "default") {
        await Promise.all([refreshDefault(), refreshGlobal()]);
      } else {
        await refreshGlobal();
      }
      setLastRefresh(new Date());
    } catch (err) {
      console.error(err);
      setError("Backend or live data service unavailable.");
    } finally {
      setLoading(false);
    }
  }, [activeSource, refreshDefault, refreshGlobal]);

  useEffect(() => {
    refreshEverything();
    const interval = setInterval(refreshEverything, REFRESH_MS);
    return () => clearInterval(interval);
  }, [refreshEverything]);

  useEffect(() => {
    if (!notificationsEnabled || !alerts.length) return;
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const latest = alerts[0];
    new Notification(`${latest.risk_level} landslide risk`, {
      body: latest.message,
    });
  }, [alerts, notificationsEnabled]);

  const counts = useMemo(() => {
    const out = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    locations.forEach((item) => {
      if (out[item.risk_level] !== undefined) out[item.risk_level] += 1;
    });
    return out;
  }, [locations]);

  const pieData = [
    { name: "LOW", value: counts.LOW },
    { name: "MEDIUM", value: counts.MEDIUM },
    { name: "HIGH", value: counts.HIGH },
    { name: "CRITICAL", value: counts.CRITICAL },
  ].filter((item) => item.value > 0);

  const runRiskForCoordinates = useCallback(
    async (latitude, longitude, label = "Selected Location") => {
      setBusy(true);
      try {
        const result = await apiGet(
          `/api/risk-by-coordinates?latitude=${latitude}&longitude=${longitude}`
        );
        const merged = {
          ...result,
          searched_place: label,
          location: label,
          latitude,
          longitude,
        };
        setRisk(merged);
        setActiveSource("custom");
        setHistory([]);
        setSelectedCoordinate({ latitude, longitude });
        setSelectedLocation(null);
        setFocusCoordinate({ latitude, longitude });
        setError("");
      } catch (err) {
        console.error(err);
        setError("Unable to calculate risk for this coordinate.");
      } finally {
        setBusy(false);
      }
    },
    []
  );

  const performSearch = async () => {
    const query = searchQuery.trim();
    if (!query) return;

    setBusy(true);
    setSearchResults([]);
    try {
      // First use known NER monitoring points.
      const local = locations.filter((item) =>
        [item.location_name, item.district, item.state]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query.toLowerCase()))
      );

      if (local.length > 0) {
        setSearchResults(
          local.slice(0, 8).map((item) => ({
            ...item,
            search_source: "NER monitoring database",
          }))
        );
        setBusy(false);
        return;
      }

      // Fallback to Open-Meteo geocoding via its public API.
      const response = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=8&language=en&format=json`
      );
      if (!response.ok) throw new Error("Geocoding failed");
      const data = await response.json();
      const results = (data.results || []).map((place) => ({
        id: `geo-${place.id}`,
        location_name: place.name,
        district: place.admin2 || place.admin1 || "",
        state: place.admin1 || "",
        country: place.country || "",
        latitude: place.latitude,
        longitude: place.longitude,
        search_source: "Open-Meteo geocoding",
      }));
      setSearchResults(results);
      if (!results.length) setError(`No location found for “${query}”.`);
    } catch (err) {
      console.error(err);
      setError("Location search failed.");
    } finally {
      setBusy(false);
    }
  };

  const handleSearchResult = (item) => {
    const label = item.location_name || "Selected Location";
    runRiskForCoordinates(item.latitude, item.longitude, label);
    setSearchResults([]);
    setSearchQuery(label);
  };

const useCurrentLocation = () => {
  if (!navigator.geolocation) {
    setError("Geolocation is not supported by this browser.");
    return;
  }

  setBusy(true);
  setError("");

  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      const { latitude, longitude } = coords;

      console.log("Current location:", latitude, longitude);
      console.log("Location accuracy:", coords.accuracy, "meters");

      runRiskForCoordinates(
        latitude,
        longitude,
        "My Current Location"
      ).finally(() => {
        setBusy(false);
      });
    },

    (geoError) => {
      setBusy(false);

      if (geoError.code === 1) {
        setError(
          "Please allow location permission in your browser."
        );
      } else {
        setError(
          "Unable to get your current location. Please try again."
        );
      }
    },

    {
      enableHighAccuracy: true,
      timeout: 30000,
      maximumAge: 0,
    }
  );
};
  const useManualLocation = () => {
    const lat = Number(manualLat);
    const lon = Number(manualLon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setError("Enter valid latitude (-90 to 90) and longitude (-180 to 180).");
      return;
    }
    runRiskForCoordinates(lat, lon, "Manual Location");
  };

  const acknowledgeAlert = async (id) => {
    try {
      await apiPost(`/api/alerts/${id}/acknowledge`);
      const updated = await apiGet("/api/alerts?status=ACTIVE");
      setAlerts(updated);
    } catch (err) {
      console.error(err);
      setError("Could not acknowledge alert.");
    }
  };

  const enableNotifications = async () => {
    if (!("Notification" in window)) {
      setError("Browser notifications are not supported.");
      return;
    }
    const permission = await Notification.requestPermission();
    setNotificationsEnabled(permission === "granted");
  };

  const refreshTerrain = async () => {
    setTerrainBusy(true);
    try {
      await apiPost("/api/terrain/refresh-all");
      await refreshGlobal();
      setError("");
    } catch (err) {
      console.error(err);
      setError("Terrain refresh failed. Check the backend/elevation service.");
    } finally {
      setTerrainBusy(false);
    }
  };

  const selectMarker = (location) => {
    setActiveSource("default");
    setSelectedLocation(location);
    setRisk((current) => ({ ...current, ...location, searched_place: location.location_name }));
    setSelectedCoordinate({
      latitude: location.latitude,
      longitude: location.longitude,
    });
    setFocusCoordinate({
      latitude: location.latitude,
      longitude: location.longitude,
    });
  };

  const handleMapClick = ({ latitude, longitude }) => {
    runRiskForCoordinates(latitude, longitude, "Map Selected Location");
  };

  const submitCitizenReport = async (event) => {
    event.preventDefault();
    if (!reportForm.description.trim()) return setError("Please describe the field observation.");
    const point = selectedCoordinate || { latitude: Number(risk?.latitude || 25.5), longitude: Number(risk?.longitude || 92.5) };
    const form = new FormData();
    form.append("description", reportForm.description);
    form.append("latitude", String(point.latitude));
    form.append("longitude", String(point.longitude));
    form.append("report_type", reportForm.type);
    form.append("reporter_name", reportForm.reporter || "Citizen");
    form.append("location_name", risk?.searched_place || risk?.location || "Selected Location");
    if (reportFile) form.append("media", reportFile);
    try {
      await apiPost("/api/citizen-reports", form);
      setReportForm((v) => ({ ...v, description: "" }));
      setReportFile(null);
      setError("Citizen report submitted successfully.");
    } catch (err) { setError(err.message || "Citizen report failed."); }
  };

  const submitRoadReport = async (event) => {
    event.preventDefault();
    if (!roadForm.road.trim()) return setError("Enter a road name.");
    const point = selectedCoordinate || { latitude: Number(risk?.latitude || 25.5), longitude: Number(risk?.longitude || 92.5) };
    const form = new FormData();
    form.append("road_name", roadForm.road);
    form.append("status", roadForm.status);
    form.append("latitude", String(point.latitude));
    form.append("longitude", String(point.longitude));
    form.append("description", roadForm.description);
    form.append("reported_by", roadForm.reporter || "Field Official");
    try {
      await apiPost("/api/road-reports", form);
      setRoadForm((v) => ({ ...v, road: "", description: "" }));
      setRoadReports(await apiGet("/api/road-reports"));
      setError("");
    } catch (err) { setError(err.message || "Road report failed."); }
  };

  const exportLocations = () => {
    const headers = [
      "Location", "State", "District", "Latitude", "Longitude",
      "Temperature", "Rainfall_24h", "Slope_degree", "Risk_score", "Risk_level"
    ];
    const rows = locations.map((item) => [
      item.location_name, item.state, item.district, item.latitude, item.longitude,
      item.temperature ?? "", item.rainfall_24h ?? "", item.slope_degree ?? "",
      item.risk_score ?? "", item.risk_level ?? ""
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ner_landslide_live_monitoring.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`app-shell ${currentIsRaining ? "weather-rain" : ""}`}>
      {currentIsRaining && (
        <div className="rain-layer" aria-hidden="true">
          {Array.from({ length: 60 }, (_, i) => (
            <span
              key={i}
              className="rain-streak"
              style={{
                left: `${(i * 29) % 100}%`,
                animationDelay: `${-((i * 13) % 28) / 10}s`,
                animationDuration: `${0.7 + ((i * 17) % 9) / 10}s`,
                opacity: 0.2 + ((i * 11) % 50) / 100,
              }}
            />
          ))}
        </div>
      )}

      <main className="dashboard">
        <header className="topbar">
          <div>
            <div className="eyebrow">DISASTER MANAGEMENT • NER</div>
            <h1>{t.title}</h1>
            <p>{t.subtitle}</p>
          </div>
          <div className="topbar-actions">
            <select className="language-select" value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Language">
              <option value="en">English</option><option value="ta">தமிழ்</option><option value="hi">हिन्दी</option><option value="te">తెలుగు</option><option value="kn">ಕನ್ನಡ</option><option value="ml">മലയാളം</option><option value="bn">বাংলা</option><option value="mr">मराठी</option><option value="gu">ગુજરાતી</option><option value="pa">ਪੰਜਾਬੀ</option><option value="or">ଓଡ଼ିଆ</option><option value="as">অসমীয়া</option><option value="ur">اردو</option>
            </select>
            <button className="ghost-btn" onClick={enableNotifications}>
              🔔 {notificationsEnabled ? t.enabled : t.alerts}
            </button>
            <div className="live-chip"><span /> LIVE</div><button className="ghost-btn" onClick={onLogout}>{t.logout}</button>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="control-panel">
          <div className="search-row">
            <div className="search-input-wrap">
              <span>⌕</span>
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && performSearch()}
                placeholder={t.search}
              />
            </div>
            <button className="primary-btn" onClick={performSearch} disabled={busy}>
              {busy ? "Working…" : t.searchBtn}
            </button>
            <button className="location-btn" onClick={useCurrentLocation} disabled={busy}>
              📍 Use My Location
            </button>
            {activeSource !== "default" && (
              <button className="mini-btn reset-btn" onClick={() => {
                setActiveSource("default");
                setSelectedCoordinate(null);
                setSelectedLocation(null);
                setSearchResults([]);
                setSearchQuery("");
                refreshDefault();
              }}>
                ↺ NER Focus
              </button>
            )}
          </div>
          {searchResults.length > 0 && (
            <div className="search-results">
              {searchResults.map((item) => (
                <button key={item.id} className="search-result" onClick={() => handleSearchResult(item)}>
                  <div>
                    <strong>📍 {item.location_name}</strong>
                    <small>{item.district}{item.state ? `, ${item.state}` : ""}</small>
                  </div>
                  <span>{item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="control-panel manual-location-panel">
          <div className="panel-kicker">{t.manual}</div>
          <div className="search-row">
            <input type="number" step="any" value={manualLat} onChange={(e) => setManualLat(e.target.value)} placeholder="Latitude" />
            <input type="number" step="any" value={manualLon} onChange={(e) => setManualLon(e.target.value)} placeholder="Longitude" />
            <button className="secondary-btn" onClick={useManualLocation} disabled={busy}>{t.calculate}</button>
            <span className="muted">Use map click, GPS, city search, or exact coordinates.</span>
          </div>
        </section>

        <section className="hero-grid">
          <div className="selected-hero">
            <div className="hero-label">{t.focus}</div>
            <h2>📍 {risk?.searched_place || risk?.location || "Loading…"}</h2>
            <p>{risk?.district}{risk?.district && risk?.state ? ", " : ""}{risk?.state}</p>
            <div className="coordinate-row">
              <span>LAT {Number(risk?.latitude || 0).toFixed(4)}</span>
              <span>LON {Number(risk?.longitude || 0).toFixed(4)}</span>
              <span>UPDATED {formatTime(risk?.recorded_at)}</span>
            </div>
          </div>

          <div className="hero-risk">
            <div>
              <div className="hero-label">{t.risk}</div>
              <div className="risk-score-big">{risk?.risk_score ?? "—"}<small>/100</small></div>
            </div>
            <div className={riskClass(risk?.risk_level)}>{risk?.risk_level || "UNKNOWN"}</div>
          </div>
        </section>

        <section className="kpi-grid">
          <div className="kpi-card accent-green">
            <span>RAIN 24H</span>
            <strong>{risk?.rainfall_24h ?? 0}<small> mm</small></strong>
            <em>{risk?.rainfall_6h ?? 0} mm / 6h</em>
          </div>
          <div className="kpi-card accent-orange">
            <span>SLOPE</span>
            <strong>{risk?.slope_degree ?? 0}<small>°</small></strong>
            <em>{risk?.elevation_m ?? "—"} m elevation</em>
          </div>
          <div className="kpi-card accent-blue">
            <span>TEMPERATURE</span>
            <strong>{risk?.temperature ?? "—"}<small>°C</small></strong>
            <em>{risk?.precipitation_probability_max ?? 0}% rain probability</em>
          </div>
          <div className="kpi-card accent-cyan">
            <span>SOIL MOISTURE</span>
            <strong>{risk?.soil_moisture_0_7cm != null ? (risk.soil_moisture_0_7cm * 100).toFixed(0) : "—"}<small>%</small></strong>
            <em>0–7 cm model layer</em>
          </div>
          <div className="kpi-card accent-purple">
            <span>NEXT 6H RAIN</span>
            <strong>{risk?.forecast_rain_6h ?? 0}<small> mm</small></strong>
            <em>Forecast context</em>
          </div>
        </section>

        {(risk?.risk_level === "HIGH" || risk?.risk_level === "CRITICAL") && (
          <div className="danger-banner">
            <div className="danger-icon">!</div>
            <div>
              <strong>{risk.risk_level} RISK CONDITION DETECTED</strong>
              <p>Review live rainfall, terrain and field information before making operational decisions.</p>
            </div>
          </div>
        )}

        <section className="content-grid main-grid">
          <div className="panel map-panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">GIS INTELLIGENCE</div>
                <h3>NER Live Risk Map</h3>
              </div>
              <div className="map-actions">
                <button className={satelliteEnabled ? "mini-btn active" : "mini-btn"} onClick={() => setSatelliteEnabled((v) => !v)}>
                  🛰 {satelliteEnabled ? "Satellite On" : "Satellite"}
                </button>
                <button className="mini-btn" onClick={refreshTerrain} disabled={terrainBusy}>
                  ⛰ {terrainBusy ? "Refreshing…" : "Refresh Terrain"}
                </button>
                <button className="mini-btn" onClick={exportLocations}>
                  ⇩ Export CSV
                </button>
              </div>
            </div>
            <div className="legend">
              {Object.entries(RISK_COLORS).map(([level, color]) => (
                <span key={level}><i style={{ background: color }} /> {level}</span>
              ))}
            </div>
            <div className="map-wrap">
              <MapView
                locations={locations}
                selectedLocation={selectedLocation}
                selectedCoordinate={selectedCoordinate}
                onMarkerSelect={selectMarker}
                onMapClick={handleMapClick}
                focusCoordinate={focusCoordinate}
                satelliteEnabled={satelliteEnabled}
              />
            </div>
            <p className="map-hint">Click a monitoring marker for details. Click any open area to calculate a coordinate-based live risk.</p>
          </div>

          <aside className="panel focus-panel">
            <div className="panel-kicker">LOCATION INTELLIGENCE</div>
            <h3>{selectedLocation?.location_name || risk?.searched_place || risk?.location || "Selected location"}</h3>
            <p className="muted">{selectedLocation ? `${selectedLocation.district}, ${selectedLocation.state}` : "Live risk details"}</p>
            <div className="focus-risk-row">
              <div className="focus-score">{selectedLocation?.risk_score ?? risk?.risk_score ?? "—"}<small>/100</small></div>
              <div className={riskClass(selectedLocation?.risk_level || risk?.risk_level)}>{selectedLocation?.risk_level || risk?.risk_level || "UNKNOWN"}</div>
            </div>
            <div className="metric-list">
              <div><span>Rainfall 24h</span><strong>{selectedLocation?.rainfall_24h ?? risk?.rainfall_24h ?? 0} mm</strong></div>
              <div><span>Slope</span><strong>{selectedLocation?.slope_degree ?? risk?.slope_degree ?? 0}°</strong></div>
              <div><span>Elevation</span><strong>{selectedLocation?.elevation_m ?? risk?.elevation_m ?? "—"} m</strong></div>
              <div><span>Temperature</span><strong>{selectedLocation?.temperature ?? risk?.temperature ?? "—"}°C</strong></div>
              <div><span>Rain score</span><strong>{selectedLocation?.rainfall_score ?? risk?.rainfall_score ?? 0}/100</strong></div>
              <div><span>Slope score</span><strong>{selectedLocation?.slope_score ?? risk?.slope_score ?? 0}/100</strong></div>
            </div>
            <div className="source-box">
              <span>Terrain source</span>
              <strong>{risk?.slope_source || "Stored terrain data"}</strong>
            </div>
          </aside>
        </section>

        <section className="content-grid secondary-grid">
          <div className="panel chart-panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">TIME SERIES</div>
                <h3>{t.history}</h3>
              </div>
              <span className="muted">Last {history.length || 0} records</span>
            </div>
            {history.length ? (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="recorded_at" tickFormatter={formatTime} stroke="#64748b" />
                    <YAxis domain={[0, 100]} stroke="#64748b" />
                    <Tooltip labelFormatter={formatTime} />
                    <Area type="monotone" dataKey="risk_score" stroke="#38bdf8" fill="url(#riskFill)" strokeWidth={3} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty-state">📈 Risk history will populate as monitoring snapshots are collected.</div>
            )}
          </div>

          <div className="panel distribution-panel">
            <div className="panel-kicker">REGIONAL STATUS</div>
            <h3>Risk Distribution</h3>
            <div className="distribution-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={4}>
                    {pieData.map((entry) => <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="distribution-center">
                <strong>{locations.length}</strong>
                <span>points</span>
              </div>
            </div>
            <div className="status-list">
              {Object.entries(counts).map(([level, count]) => (
                <div key={level}><span><i style={{ background: RISK_COLORS[level] }} />{level}</span><strong>{count}</strong></div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel state-panel">
          <div className="panel-head">
            <div>
              <div className="panel-kicker">REGIONAL BREAKDOWN</div>
              <h3>State Risk Overview</h3>
            </div>
            <span className="muted">Latest stored risk snapshots</span>
          </div>
          {stateSummary.length ? (
            <div className="state-table-wrap">
              <table className="state-table">
                <thead>
                  <tr><th>State</th><th>Points</th><th>Avg risk</th><th>High/Critical</th></tr>
                </thead>
                <tbody>
                  {stateSummary.map((row) => (
                    <tr key={row.state}>
                      <td>{row.state}</td>
                      <td>{row.locations}</td>
                      <td>{row.avg_risk_score ?? "—"}</td>
                      <td>{row.high_or_critical}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state compact">State-level risk data will appear after live snapshots are stored.</div>
          )}
        </section>

        <section className="content-grid lower-grid">
          <div className="panel alerts-panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">EARLY WARNING</div>
                <h3>{t.activeAlerts}</h3>
              </div>
              <span className="alert-count">{analytics?.active_alerts ?? alerts.length}</span>
            </div>
            {alerts.length ? (
              <div className="alert-list">
                {alerts.map((alert) => (
                  <div key={alert.id} className="alert-item">
                    <div className={`alert-level ${alert.risk_level.toLowerCase()}`}>{alert.risk_level}</div>
                    <div className="alert-content">
                      <strong>{alert.location_name || "Location"}</strong>
                      <p>{alert.message}</p>
                      <small>{formatTime(alert.created_at)}</small>
                    </div>
                    <button className="mini-btn" onClick={() => acknowledgeAlert(alert.id)}>Acknowledge</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">✅ No active high/critical alerts.</div>
            )}
          </div>

          <div className="panel ai-panel">
            <div className="panel-kicker">AI / ML READINESS</div>
            <h3>Experimental Model</h3>
            <div className="ai-status">
              <span className={`status-dot ${modelStatus?.available ? "ready" : "pending"}`} />
              {modelStatus?.available ? "Model artifact available" : "Model not trained"}
            </div>
            <div className="ai-stats">
              <div><span>Labeled samples</span><strong>{modelStatus?.samples_available ?? 0}</strong></div>
              <div><span>Training ready</span><strong>{modelStatus?.ready_for_training ? "YES" : "NO"}</strong></div>
              <div><span>Minimum samples</span><strong>{modelStatus?.minimum_samples ?? 30}</strong></div>
            </div>
            {modelStatus?.metadata?.accuracy != null && (
              <div className="ai-metrics">
                <div><span>Accuracy</span><strong>{(modelStatus.metadata.accuracy * 100).toFixed(1)}%</strong></div>
                <div><span>F1</span><strong>{(modelStatus.metadata.f1 * 100).toFixed(1)}%</strong></div>
                <div><span>ROC-AUC</span><strong>{(modelStatus.metadata.roc_auc * 100).toFixed(1)}%</strong></div>
              </div>
            )}
            <p className="ai-note">The application keeps ML output separate from the live prototype risk index until representative historical labels and validation are available.</p>
            <button className="secondary-btn" onClick={async () => {
              try {
                const result = await apiPost("/api/ml/train");
                setModelStatus((prev) => ({ ...prev, available: true, metadata: result }));
              } catch (err) {
                setError(err.message || "Model training failed.");
              }
            }}>Train / Refresh Model</button>
          </div>
        </section>


        <section className="content-grid lower-grid">
          <div className="panel report-panel">
            <div className="panel-kicker">CITIZEN / FIELD REPORTING</div>
            <h3>{t.report}</h3>
            <p className="muted">Attach a photo/video and submit it at the selected coordinate. Uploaded media is visible to administrators only.</p>
            <form className="report-form" onSubmit={submitCitizenReport}>
              <div className="form-grid">
                <select value={reportForm.type} onChange={(e) => setReportForm({...reportForm, type: e.target.value})}>
                  <option value="OBSERVATION">General observation</option><option value="CRACK">Ground crack</option><option value="SLOPE_MOVEMENT">Slope movement</option><option value="BLOCKED_ROAD">Blocked road</option><option value="FLOODING">Flooding</option>
                </select>
                <input value={reportForm.reporter} onChange={(e) => setReportForm({...reportForm, reporter: e.target.value})} placeholder="Reporter name" />
              </div>
              <textarea value={reportForm.description} onChange={(e) => setReportForm({...reportForm, description: e.target.value})} placeholder="Describe cracks, slope movement, blockage or flooding..." rows="3" />
              <input type="file" accept="image/*,video/*,.pdf,.doc,.docx" onChange={(e) => setReportFile(e.target.files?.[0] || null)} />
              <button className="secondary-btn" type="submit">Submit geo-tagged report</button>
            </form>
            <div className="mini-list"><div className="mini-item"><strong>PRIVATE</strong><span>Submitted report media and documents are available in the Admin Console only.</span></div></div>
          </div>

          <div className="panel report-panel">
            <div className="panel-kicker">ROAD CONNECTIVITY</div>
            <h3>Road status & emergency prioritisation</h3>
            <p className="muted">Field officials can publish OPEN, RESTRICTED or BLOCKED road conditions.</p>
            <form className="report-form" onSubmit={submitRoadReport}>
              <div className="form-grid">
                <input value={roadForm.road} onChange={(e) => setRoadForm({...roadForm, road: e.target.value})} placeholder="Road / highway name" />
                <select value={roadForm.status} onChange={(e) => setRoadForm({...roadForm, status: e.target.value})}><option>BLOCKED</option><option>RESTRICTED</option><option>OPEN</option></select>
              </div>
              <textarea value={roadForm.description} onChange={(e) => setRoadForm({...roadForm, description: e.target.value})} placeholder="Reason / response information" rows="3" />
              <button className="secondary-btn" type="submit">Publish road status</button>
            </form>
            <div className="mini-list">{roadReports.slice(0, 6).map((r) => <div className="mini-item" key={r.id}><strong>{r.status} • {r.road_name}</strong><span>{r.description || "No description"}</span><small>{Number(r.latitude).toFixed(4)}, {Number(r.longitude).toFixed(4)}</small></div>)}</div>
          </div>
        </section>

        <section className="panel integration-panel">
          <div className="panel-kicker">FIELD + SENSOR + SATELLITE INTEGRATION</div>
          <div className="integration-grid">
            <div><strong>🛰 Satellite context</strong><span>NASA GIBS MODIS true-colour overlay for visual inspection. Not treated as a validated ML feature.</span></div>
            <div><strong>📡 Soil sensor ready</strong><span>REST ingestion endpoint accepts soil moisture, vibration and battery readings from ESP32/Arduino gateways.</span></div>
            <div><strong>📶 Low-network ready</strong><span>Core UI assets are cached by the service worker; field reports can be retried after connectivity returns.</span></div>
            <div><strong>🔔 Early warning</strong><span>Dashboard + browser notifications are implemented. SMS can be connected later through an SMS provider.</span></div>
          </div>
        </section>

        <footer className="footer-bar">
          <div><span>System status</span><strong>Operational</strong></div>
          <div><span>Monitoring points</span><strong>{locations.length}</strong></div>
          <div><span>Refresh cycle</span><strong>5 min</strong></div>
          <div><span>Last refresh</span><strong>{lastRefresh ? formatTime(lastRefresh) : "—"}</strong></div>
          <div><span>API</span><strong>{API_BASE.replace(/^https?:\/\//, "")}</strong></div>
        </footer>

        <div className="attribution-note">
          Weather/elevation data: Open-Meteo with Copernicus DEM attribution. Satellite context: NASA GIBS. Prototype risk thresholds require local validation.
        </div>
      </main>
    </div>
  );
}

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("register");
  const [admin, setAdmin] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    aadhaar: "",
    password: "",
    confirmPassword: "",
    username: "admin",
  });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      const fd = new FormData();

      if (admin) {
        fd.append("username", form.username);
        fd.append("password", form.password);
        const result = await apiPost("/api/auth/admin-login", fd);
        localStorage.setItem("landslide_token", result.token);
        onAuth({ ...result });
        return;
      }

      fd.append("email", form.email);
      fd.append("password", form.password);

      if (mode === "register") {
        if (form.password !== form.confirmPassword) {
          throw new Error("Passwords do not match.");
        }
        fd.append("name", form.name);
        fd.append("phone", form.phone);
        fd.append("aadhaar", form.aadhaar);

        const result = await apiPost("/api/auth/register", fd);
        localStorage.setItem("landslide_token", result.token);
        onAuth(result);
      } else {
        const result = await apiPost("/api/auth/login", fd);
        localStorage.setItem("landslide_token", result.token);
        const me = await apiGet("/api/auth/me");
        onAuth(me);
      }
    } catch (err) {
      setMessage(err.message || "Authentication failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="eyebrow">NER DISASTER MANAGEMENT</div>
        <h1>AI Landslide Early Warning</h1>
        <p className="muted">
          User access, location-based risk monitoring and private field reports.
        </p>

        <div className="auth-tabs">
          <button
            className={mode === "register" && !admin ? "active" : ""}
            onClick={() => {
              setAdmin(false);
              setMode("register");
              setMessage("");
            }}
          >
            New User
          </button>
          <button
            className={mode === "login" && !admin ? "active" : ""}
            onClick={() => {
              setAdmin(false);
              setMode("login");
              setMessage("");
            }}
          >
            User Login
          </button>
          <button
            className={admin ? "active" : ""}
            onClick={() => {
              setAdmin(true);
              setMessage("");
            }}
          >
            Admin
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          {admin ? (
            <>
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="Admin username"
                required
              />
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Admin password"
                required
              />
            </>
          ) : (
            <>
              {mode === "register" && (
                <>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Full name"
                    required
                  />
                  <input
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="Phone number"
                    required
                  />
                  <input
                    value={form.aadhaar}
                    onChange={(e) => setForm({ ...form, aadhaar: e.target.value })}
                    placeholder="Aadhaar number (12 digits)"
                    inputMode="numeric"
                    required
                  />
                </>
              )}

              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Email address"
                required
              />

              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Password (minimum 8 characters)"
                minLength={8}
                required
              />

              {mode === "register" && (
                <input
                  type="password"
                  value={form.confirmPassword}
                  onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                  placeholder="Confirm password"
                  minLength={8}
                  required
                />
              )}
            </>
          )}

          <button className="primary-btn" disabled={busy}>
            {busy
              ? "Please wait…"
              : admin
                ? "Admin Login"
                : mode === "register"
                  ? "Create Account"
                  : "Login"}
          </button>
        </form>

        {message && <div className="error-banner">{message}</div>}

        <small className="muted">
          Email OTP verification has been removed. Passwords are stored as one-way
          hashes; Aadhaar is stored only as a one-way hash. This prototype does not
          claim UIDAI authentication.
        </small>
      </div>
    </div>
  );
}

function AdminPage({ auth, onLogout }) {
  const [reports, setReports] = useState([]); const [roads, setRoads] = useState([]); const [error, setError] = useState("");
  const load = async () => { try { setReports(await apiGet("/api/admin/reports")); setRoads(await apiGet("/api/admin/road-reports")); } catch (e) { setError(e.message); } };
  const openMedia = async (id) => {
    try {
      const token = localStorage.getItem("landslide_token");
      const response = await fetch(`${API_BASE}/api/citizen-reports/${id}/media`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("Media access denied");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);
  return <div className="auth-shell"><div className="admin-shell">
    <header className="topbar"><div><div className="eyebrow">ADMIN CONSOLE</div><h1>NER Field Reports & Alerts</h1><p>Private administrator view for citizen uploads and operational reports.</p></div><button className="ghost-btn" onClick={onLogout}>Logout</button></header>
    {error && <div className="error-banner">{error}</div>}
    <div className="admin-grid"><section className="panel"><div className="panel-kicker">CITIZEN MEDIA / DOCUMENTS</div><h3>Submitted reports</h3>{reports.length ? reports.map(r => <div className="admin-report" key={r.id}><strong>{r.report_type} • {r.reporter_name || "Citizen"}</strong><p>{r.description}</p><small>{r.location_name || "Selected location"} • {Number(r.latitude).toFixed(5)}, {Number(r.longitude).toFixed(5)} • {formatTime(r.created_at)}</small>{r.media_filename && <button className="secondary-btn" onClick={() => openMedia(r.id)}>View uploaded {r.media_content_type?.startsWith("video") ? "video" : "image/document"}</button>}</div>) : <div className="empty-state">No citizen reports yet.</div>}</section>
    <section className="panel"><div className="panel-kicker">ROAD CONNECTIVITY</div><h3>Operational reports</h3>{roads.length ? roads.map(r => <div className="admin-report" key={r.id}><strong>{r.status} • {r.road_name}</strong><p>{r.description || "No description"}</p><small>{r.reported_by || "Field official"} • {Number(r.latitude).toFixed(5)}, {Number(r.longitude).toFixed(5)}</small></div>) : <div className="empty-state">No road reports.</div>}</section></div>
    <div className="attribution-note">Admin access is protected by a server-side credential. Uploaded media is not listed on the public dashboard.</div>
  </div></div>;
}

function App() {
  const [auth, setAuth] = useState(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const token = localStorage.getItem("landslide_token");
    if (!token) { setReady(true); return; }
    apiGet("/api/auth/me")
      .then(setAuth)
      .catch(() => { localStorage.removeItem("landslide_token"); setAuth(null); })
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    const handleExpired = () => setAuth(null);
    window.addEventListener("landslide-auth-expired", handleExpired);
    return () => window.removeEventListener("landslide-auth-expired", handleExpired);
  }, []);
  const logout = () => { localStorage.removeItem("landslide_token"); setAuth(null); };
  if (!ready) return <div className="auth-shell"><div className="auth-card">Loading secure access…</div></div>;
  if (!auth) return <AuthScreen onAuth={setAuth} />;
  if (auth.role === "admin") return <AdminPage auth={auth} onLogout={logout} />;
  return <Dashboard auth={auth} onLogout={logout} />;
}

export default App;
