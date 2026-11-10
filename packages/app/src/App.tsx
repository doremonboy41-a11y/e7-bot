import React, { useEffect, useState } from 'react';
import './App.css'
import { useAppContext } from './context/AppContext';
import TopBar from './components/TopBar/TopBar'
import ControlPanel from './components/ControlPanel/ControlPanel'
import StatsContainer from './components/StatsContainer/StatsContainer'
import LogsContainer from './components/LogsContainer/LogsContainer'


const App: React.FC = () => {
  const {
    setAppVersion,
    setFastMode,
    setCurrentScreen,
    setDevMode,
    background,
    setBackground,
    panelsHidden,
    setPanelsHidden
  } = useAppContext()

  useEffect(() => {
    const handleKeyDownDevMode = (e: KeyboardEvent) => {
      if (e.key === "F2") {
        e.preventDefault();
        setPanelsHidden((val) => !val);
      } else if (e.key === "Escape") {
        setPanelsHidden(false);
      }
      if (e.key === "F1") {
        e.preventDefault();
        setDevMode((val) => !val);
        setCurrentScreen(false)
        setFastMode(false)
      }
    };

    window.addEventListener('pywebviewready', getVersion);
    window.addEventListener('pywebviewready', loadSettings);
    if (window.pywebview?.api) loadSettings()
    window.addEventListener("keydown", handleKeyDownDevMode);

    return () => {
      window.removeEventListener('pywebviewready', getVersion);
      window.removeEventListener('pywebviewready', loadSettings);
      window.removeEventListener('keydown', handleKeyDownDevMode);
    };
  }, []);

  // Full picture of the chosen background, read from the backgrounds folder
  const [backgroundUrl, setBackgroundUrl] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    if (background.image === null) {
      setBackgroundUrl(null)
      return
    }
    window.pywebview?.api?.get_background(background.image)
      .then((url: string | null) => { if (!cancelled) setBackgroundUrl(url) })
      .catch(() => { if (!cancelled) setBackgroundUrl(null) })
    return () => { cancelled = true }
  }, [background.image])

  async function loadSettings() {
    try {
      const settings = await window.pywebview.api.get_settings()
      const saved = settings?.background
      if (saved) {
        setBackground({
          image: typeof saved.image === 'string' ? saved.image : null,
          transparency: typeof saved.transparency === 'number' ? saved.transparency : 70,
        })
      }
    } catch (e) {
      // No saved settings yet
    }
  }

  async function getVersion() {
    const res = await window.pywebview.api.get_version()
    if (res) {
      setAppVersion(res.current_app_version)
    }
  }

  // A picture that cannot be read (deleted, ...) falls back to the default look
  const image = backgroundUrl
  const cardAlpha = image ? 1 - background.transparency / 100 : 1
  const style = {
    '--card-alpha': cardAlpha,
    '--log-alpha': 0.55 + 0.45 * cardAlpha,
    ...(image ? { backgroundImage: `url(${image})` } : {}),
  } as React.CSSProperties

  return (
    <div className={`app${image ? ' has-bg' : ''}${image && panelsHidden ? ' panels-hidden' : ''}`} style={style}>
      <TopBar />
      <main className='main'>
        <ControlPanel />
        <StatsContainer />
        <LogsContainer />
      </main>
    </div>
  );
};

export default App;
