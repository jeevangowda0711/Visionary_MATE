const micBtn = document.getElementById('micBtn');
const micBtnWrapper = document.getElementById('micBtnWrapper');
const video = document.createElement('video'); // Create a video element programmatically
let audioStream = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let shakeThreshold = 15;
let lastX = 0, lastY = 0, lastZ = 0;
let lastTapTime = 0;
let tapCount = 0;
let audioPlayer = null;
let videoStream = null;
let navigationInProgress = false;
let navigationData = null;
let currentStepIndex = 0;
let positionUpdateTimer = null; // For setInterval-based position updates
const positionUpdateInterval = 10000; // 10 seconds

// Start the app when the page loads
window.addEventListener('load', startApp);

async function startApp() {
    try {
        console.log('Starting app...');

        await requestPermissions();
        console.log('Permissions requested successfully');

        await setupVideoStream();
        console.log('Video stream set up successfully');

        await setupGeolocation();
        console.log('Geolocation set up successfully');

        setupMotionDetection();
        console.log('Motion detection set up successfully');

        setupInteractionDetection();
        console.log('Interaction detection set up successfully');

        console.log('App started successfully');
    } catch (error) {
        console.error('Error starting app:', error);
        handleStartupError(error);
    }
}

async function requestPermissions() {
    const permissions = ['camera', 'microphone', 'geolocation'];
    for (const permission of permissions) {
        try {
            console.log(`Requesting permission for ${permission}...`);
            if (navigator.permissions && navigator.permissions.query) {
                const result = await navigator.permissions.query({ name: permission });
                console.log(`Permission status for ${permission}: ${result.state}`);
                if (result.state === 'denied') {
                    throw new Error(`Permission for ${permission} was denied`);
                }
            } else {
                console.log(`Permissions API not available, assuming ${permission} permission is granted`);
            }
        } catch (error) {
            console.warn(`Error requesting ${permission} permission:`, error);
            throw error;
        }
    }
}

async function setupVideoStream() {
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' },
            audio: false
        });
        video.srcObject = videoStream;
        await video.play();
        console.log('Video stream set up successfully');
    } catch (error) {
        console.error('Error setting up video stream:', error);
    }
}

async function setupGeolocation() {
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject);
    });
}

function setupMotionDetection() {
    if (window.DeviceMotionEvent) {
        window.addEventListener('devicemotion', handleMotionEvent, true);
    } else {
        console.log('Device motion not supported');
    }
}

function handleMotionEvent(event) {
    if (event.accelerationIncludingGravity) {
        let acceleration = event.accelerationIncludingGravity;
        let curX = acceleration.x;
        let curY = acceleration.y;
        let curZ = acceleration.z;

        let change = Math.abs(curX + curY + curZ - lastX - lastY - lastZ);
        if (change > shakeThreshold) {
            toggleRecording();
        }

        lastX = curX;
        lastY = curY;
        lastZ = curZ;
    }
}

function handleStartupError(error) {
    let errorMessage = 'An error occurred while starting the app. ';
    if (error.name === 'NotAllowedError') {
        errorMessage += 'Please grant the necessary permissions and reload the page.';
    } else if (error.name === 'NotSupportedError') {
        errorMessage += 'Your device may not support all required features. Please try using a different device or browser.';
    } else if (error.name === 'NotFoundError') {
        errorMessage += 'Required hardware (camera or microphone) not found. Please check your device settings.';
    } else {
        errorMessage += 'Please check your device settings and try again. If the problem persists, try reloading the page.';
    }
    document.getElementById('errorMessage').textContent = errorMessage;
    document.getElementById('errorMessage').classList.remove('hidden');

    const reloadButton = document.createElement('button');
    reloadButton.textContent = 'Reload Page';
    reloadButton.className = 'bg-blue-500 text-white p-2 rounded mt-4';
    reloadButton.onclick = () => location.reload();
    document.getElementById('errorMessage').appendChild(reloadButton);
}

function setupInteractionDetection() {
    document.body.addEventListener('touchstart', handleTouch, { passive: false });
    document.body.addEventListener('mousedown', handleMouse);
}

function handleTouch(event) {
    event.preventDefault();
    handleInteraction();
}

function handleMouse(event) {
    handleInteraction();
}

function handleInteraction() {
    const currentTime = new Date().getTime();
    const tapLength = currentTime - lastTapTime;

    if (tapLength < 300 && tapLength > 50) {
        tapCount++;
        if (tapCount === 2) {
            stopAudioAndResetApp();
            tapCount = 0;
        }
    } else {
        tapCount = 1;
        toggleRecording();
    }

    lastTapTime = currentTime;

    setTimeout(() => {
        tapCount = 0;
    }, 300);

    if (navigator.vibrate) {
        navigator.vibrate(50);
    }

    playAuditoryFeedback();
}

function playAuditoryFeedback() {
    // Implement a short audio cue to confirm user actions
    // This is a placeholder and needs to be implemented
}

function stopAudioAndResetApp() {
    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
    }
    stopRecording();
    stopPositionUpdates(); // Stop position updates
    navigationInProgress = false;
    navigationData = null;
    currentStepIndex = 0;
    console.log("App reset due to double tap");
    location.reload();
}

async function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
        }
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(audioStream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = sendAudioAndImageToBackend;

        mediaRecorder.start();
        isRecording = true;
        micBtnWrapper.classList.add('recording');
        micBtn.querySelector('i').classList.add('text-red-500');
        micBtn.querySelector('i').classList.remove('text-blue-500', 'hover:text-blue-600');
    } catch (error) {
        console.error('Error starting recording:', error);
    }
}

async function sendAudioAndImageToBackend() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const imageBlob = await captureImage();

    if (!imageBlob) {
        console.error('Failed to capture image');
        playAudioResponse(await synthesize_speech("I'm sorry, but I couldn't capture an image. Please try again.", "english"));
        return;
    }

    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('image', imageBlob, 'capture.jpg');

    try {
        const response = await fetch('/process_audio_and_image', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (!result.audio) {
            throw new Error("Response does not contain audio data");
        }

        if (result.is_navigation) {
            playAudioResponse(result.audio);
            handleNavigation(result.location);
        } else if (result.is_searching) {
            playAudioResponse(result.audio);
        } else {
            playAudioResponse(result.audio);
        }
    } catch (error) {
        console.error('Error processing request:', error);
        playAudioResponse(await synthesize_speech("I'm sorry, but there was an error processing your request. Please try again.", "english"));
    }
}

async function captureImage() {
    if (!video.srcObject) {
        console.error('Video stream is not available');
        return null;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtnWrapper.classList.remove('recording');
        micBtn.querySelector('i').classList.remove('text-red-500');
        micBtn.querySelector('i').classList.add('text-blue-500', 'hover:text-blue-600');
        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
            audioStream = null;
        }
    }
}

// Implement the function to get destination coordinates from the backend
async function getDestinationCoordinates(destination, latitude, longitude) {
    try {
        const response = await fetch('/get_nearest_place', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword: destination, latitude, longitude })
        });

        if (!response.ok) {
            if (response.status === 404) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Location not found");
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        const coords = [data.longitude, data.latitude]; // [lng, lat]
        console.log('Backend returned coordinates:', coords);
        return coords;
    } catch (error) {
        console.error('Error fetching destination coordinates:', error);
        throw error;
    }
}

async function handleNavigation(destination) {
    console.log("Handling navigation for", destination);

    function handleGeolocationError(errorMessage) {
        synthesize_speech(errorMessage, "english")
            .then(audio => {
                playAudioResponse(audio);
            })
            .catch(err => {
                console.error('Error in synthesize_speech:', err);
            });
    }

    if (navigationInProgress) {
        console.log("Navigation already in progress.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const { latitude, longitude } = position.coords;
            console.log("Current Latitude:", latitude, "Longitude:", longitude);

            try {
                // Get destination coordinates from the backend
                const destinationCoords = await getDestinationCoordinates(destination, latitude, longitude);
                const [destinationLng, destinationLat] = destinationCoords;

                console.log("Destination coordinates:", destinationLat, destinationLng);

                // Use Mapbox Directions API
                const mapboxApiUrl = `https://api.mapbox.com/directions/v5/mapbox/walking/${longitude},${latitude};${destinationLng},${destinationLat}?steps=true&geometries=geojson&access_token=${window.MAPBOX_API_KEY}`;
                console.log(window.MAPBOX_API_KEY);
                const directionsResponse = await fetch(mapboxApiUrl);
                const directionsData = await directionsResponse.json();

                if (!directionsData.routes || directionsData.routes.length === 0) {
                    console.error("No routes found for the given location.");
                    playAudioResponse(await synthesize_speech("No route found. Please try again.", "english"));
                    return;
                }

                navigationData = {
                    steps: directionsData.routes[0].legs[0].steps,
                    currentStepIndex: 0,
                    destination: { latitude: destinationLat, longitude: destinationLng }
                };

                navigationInProgress = true;

                // Start monitoring position
                startPositionUpdates();

                // Provide the first instruction
                await provideCurrentInstruction();

            } catch (error) {
                console.error('Error getting directions:', error);
                playAudioResponse(await synthesize_speech(error.message || "There was an error fetching navigation data.", "english"));
            }
        },
        (error) => {
            if (error.code === 1) {
                console.error('Error: Permission denied');
                handleGeolocationError("Location access denied. Please enable location services and try again.");
            } else if (error.code === 2) {
                console.error('Error: Position unavailable');
                handleGeolocationError("Unable to access location. Please check your connection and try again.");
            } else if (error.code === 3) {
                console.error('Error: Timeout');
                handleGeolocationError("Location request timed out. Please try again.");
            } else {
                console.error('Error getting location:', error);
                handleGeolocationError("Unable to access location. Please try again.");
            }
        }
    );
}

function startPositionUpdates() {
    positionUpdateTimer = setInterval(() => {
        navigator.geolocation.getCurrentPosition(positionUpdateHandler, positionErrorHandler, {
            enableHighAccuracy: true,
            maximumAge: 0,
            timeout: 5000
        });
    }, positionUpdateInterval);
}

function stopPositionUpdates() {
    if (positionUpdateTimer) {
        clearInterval(positionUpdateTimer);
        positionUpdateTimer = null;
    }
}

async function provideCurrentInstruction() {
    if (!navigationData) return;

    const step = navigationData.steps[navigationData.currentStepIndex];
    const instruction = step.maneuver.instruction;
    console.log("Current Instruction:", instruction);
    playAudioResponse(await synthesize_speech(instruction, "english"));
}

async function positionUpdateHandler(position) {
    const { latitude, longitude } = position.coords;
    console.log("Updated Position:", latitude, longitude);

    if (!navigationData) return;

    const step = navigationData.steps[navigationData.currentStepIndex];
    const stepLocation = step.maneuver.location; // [lng, lat]
    const distance = haversineDistance([latitude, longitude], stepLocation);

    console.log(`User Position - Latitude: ${latitude}, Longitude: ${longitude}`);
    console.log(`Step Position - Latitude: ${stepLocation[1]}, Longitude: ${stepLocation[0]}`);
    console.log(`Distance to next step: ${distance.toFixed(2)} meters`);

    // Increase the distance threshold
    const distanceThreshold = 20; // 20 meters

    if (distance < distanceThreshold) {
        navigationData.currentStepIndex++;
        if (navigationData.currentStepIndex >= navigationData.steps.length) {
            console.log("Navigation complete");
            playAudioResponse(await synthesize_speech("You have arrived at your destination.", "english"));
            stopPositionUpdates(); // Stop position updates
            navigationInProgress = false;
            navigationData = null;
            return;
        }
        await provideCurrentInstruction();
    }
}


function positionErrorHandler(error) {
    console.error('Error watching position:', error);
}

function haversineDistance(coords1, coords2) {
    function toRad(x) {
        return x * Math.PI / 180;
    }

    var lat1 = coords1[0];
    var lon1 = coords1[1];

    var lat2 = coords2[1];
    var lon2 = coords2[0];

    var R = 6371000; // meters
    var dLat = toRad(lat2 - lat1);
    var dLon = toRad(lon2 - lon1);

    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);

    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    var d = R * c;

    return d;
}

function playAudioResponse(audioBase64) {
    if (!audioBase64) {
        console.error('No audio data to play.');
        return;
    }

    try {
        const base64Data = audioBase64.split(',')[1]; // Extract base64 part
        if (!base64Data) {
            throw new Error('Invalid audio data format.');
        }

        const audioBlob = base64ToBlob(base64Data, 'audio/mp3');
        const audioUrl = URL.createObjectURL(audioBlob);
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer.currentTime = 0;
        }
        audioPlayer = new Audio(audioUrl);
        audioPlayer.play().catch(error => {
            console.error('Audio playback failed:', error);
        });
    } catch (error) {
        console.error('Invalid base64 string for audio:', error);
    }
}

function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

async function synthesize_speech(text, language) {
    try {
        const response = await fetch('/synthesize_speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, language })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.error) {
            console.error('Error from synthesize_speech endpoint:', result.error);
            return null;
        }

        return result.audio; // Base64 encoded audio data
    } catch (error) {
        console.error('Error synthesizing speech:', error);
        return null;
    }
}
