let currentApp = 'home';

function setActiveApp(app) {
  const toggle = document.getElementById('toggle');
  const spans = toggle.getElementsByTagName('span');
  
  for (let span of spans) {
    span.style.fontWeight = 'normal';
  }

  if (app === 'visionary') {
    spans[0].style.fontWeight = 'bold';
  } else if (app === 'mate') {
    spans[2].style.fontWeight = 'bold';
  } else {
    spans[1].style.fontWeight = 'bold';
  }
}

// Call this function when the page loads to set the correct active app
document.addEventListener('DOMContentLoaded', () => {
  const currentPath = window.location.pathname;
  if (currentPath.includes('/visionary')) {
    setActiveApp('visionary');
  } else if (currentPath.includes('/mate')) {
    setActiveApp('mate');
  } else {
    setActiveApp('home');
  }
});

async function loadAppContent(appRoute) {
  try {
    const response = await fetch(appRoute);
    const text = await response.text();
    document.getElementById('app-content').innerHTML = text;
  } catch (error) {
    console.error('Error loading app:', error);
  }
}
