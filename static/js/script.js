
document.addEventListener('DOMContentLoaded', function() {
    const webcamContainer = document.getElementById('webcam-container');
    const startButton = document.getElementById('start-webcam');
    const captureButton = document.getElementById('capture-btn');
    const retakeButton = document.getElementById('retake-btn');
    const startButtons = document.getElementById('start-buttons');
    const captureButtons = document.getElementById('capture-buttons');
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('canvas');
    const fileInput = document.getElementById('file');
    let stream = null;
  
    // Start webcam
    if (startButton) {
        startButton.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment' 
            }, 
            audio: false 
            });
            
            video.srcObject = stream;
            webcamContainer.style.display = 'block';
            captureButtons.style.display = 'block';
            startButtons.style.display = 'none';
            
            // Hide file upload when using webcam
            const cardLeft = document.querySelector('.card-left');
            if(cardLeft) cardLeft.style.display = 'none';

        } catch (err) {
            console.error('Error accessing webcam:', err);
            alert('Could not access webcam. Please check permissions and try again.');
        }
        });
    }
  
    // Capture image from webcam
    if (captureButton) {
        captureButton.addEventListener('click', () => {
        if (!stream) return;
        
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext('2d');
        
        // Draw current video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Stop all video tracks
        stream.getTracks().forEach(track => track.stop());
        
        // Show captured image
        video.style.display = 'none';
        canvas.style.display = 'block';
        
        // Change button text
        captureButton.innerHTML = '<i class="fas fa-search me-2"></i>Identify Plant';
        captureButton.onclick = identifyPlant;
        });
    }
  
    // Retake photo
    if (retakeButton) {
        retakeButton.addEventListener('click', () => {
        // Show video again
        video.style.display = 'block';
        canvas.style.display = 'none';
        
        // Restart webcam
        startButton.click();
        });
    }
  
    async function identifyPlant() {
      try {
          // Show loading state
          const captureBtn = document.getElementById('capture-btn');
          captureBtn.disabled = true;
          captureBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Identifying...';
          
          // Convert canvas to blob
          canvas.toBlob(async (blob) => {
              try {
                  const formData = new FormData();
                  formData.append('file', blob, 'capture.jpg');
                  
                  // Send to your upload endpoint
                  const response = await fetch('/upload', {
                      method: 'POST',
                      headers: {
                          'X-Requested-With': 'XMLHttpRequest'
                      },
                      body: formData
                  });
                  
                  const data = await response.json();
                  
                  if (response.ok) {
                      // If we get a success response, create and show the result card
                      const resultHtml = `
                          <div class="card mt-4" style="max-width: 700px; margin: 0 auto;">
                              <div class="card-header bg-success text-white">
                                  <h5 class="mb-0">Identification Result</h5>
                              </div>
                              <div class="card-body">
                                  <div class="row">
                                      <div class="col-md-6">
                                          <img src="${data.image_url}" class="img-fluid rounded" alt="Captured plant">
                                      </div>
                                      <div class="col-md-6">
                                          <h4>${data.plant_name}</h4>
                                          <p class="text-muted">${data.scientific_name}</p>
                                          <h6>Medicinal Properties:</h6>
                                          <p>${data.medicinal_properties || 'No information available'}</p>
                                          <h6>Growing Conditions:</h6>
                                          <p>${data.growing_conditions || 'No information available'}</p>
                                      </div>
                                  </div>
                              </div>
                              <div class="card-footer text-end">
                                  <button class="btn btn-primary" onclick="location.reload()">
                                      <i class="fas fa-redo me-2"></i>Try Another Plant
                                  </button>
                              </div>
                          </div>
                      `;
                      
                      // Replace webcam container with results
                      const webcamContainer = document.getElementById('webcam-container');
                      webcamContainer.innerHTML = resultHtml;
                  } else {
                      throw new Error(data.error || 'Failed to identify plant');
                  }
              } catch (error) {
                  console.error('Error:', error);
                  alert(error.message || 'Failed to identify plant. Please try again.');
                  captureBtn.disabled = false;
                  captureBtn.innerHTML = '<i class="fas fa-search me-2"></i>Identify Plant';
              }
          }, 'image/jpeg', 0.9);
          
      } catch (error) {
          console.error('Error capturing image:', error);
          alert('Error capturing image. Please try again.');
          const captureBtn = document.getElementById('capture-btn');
          captureBtn.disabled = false;
          captureBtn.innerHTML = '<i class="fas fa-search me-2"></i>Identify Plant';
      }
  }
           
    // Clean up webcam on page unload
    window.addEventListener('beforeunload', () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    });
    
    // Toggle between webcam and file upload
    function toggleUploadMethod(showWebcam) {
      const cardLeft = document.querySelector('.card-left');
      if (cardLeft) cardLeft.style.display = showWebcam ? 'none' : 'block';
      if (!showWebcam && stream) {
        stream.getTracks().forEach(track => track.stop());
        webcamContainer.style.display = 'none';
        captureButtons.style.display = 'none';
        startButtons.style.display = 'block';
      }
    }
    
    // Add event listener to file input to switch back to file upload
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (stream) {
            toggleUploadMethod(false);
            }
        });
    }
    
    // Add a button to switch back to file upload
    const existingSwitchBtn = document.getElementById('switch-to-upload-btn');
    if (!existingSwitchBtn && document.getElementById('capture-buttons')) {
        const switchToUploadBtn = document.createElement('button');
        switchToUploadBtn.id = 'switch-to-upload-btn';
        switchToUploadBtn.className = 'btn btn-sm btn-outline-secondary mt-2';
        switchToUploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i> Upload Image Instead';
        switchToUploadBtn.onclick = () => toggleUploadMethod(false);
        document.getElementById('capture-buttons').appendChild(switchToUploadBtn);
    }
  });
  
    // ---------- file input UI ----------
    const fileInputElem = document.getElementById('file');
    if (fileInputElem) {
        fileInputElem.addEventListener('change', function(e) {
            const fileName = e.target.files[0] ? e.target.files[0].name : 'No file selected';
            const fileNameElem = document.getElementById('fileName');
            if (fileNameElem) fileNameElem.textContent = fileName;
            const fileLabel = document.getElementById('fileLabel');
            if (fileLabel) {
                if (e.target.files.length > 0) {
                fileLabel.style.borderColor = '#2E7D32';
                fileLabel.style.backgroundColor = '#F1F8E9';
                } else {
                fileLabel.style.borderColor = '#81C784';
                fileLabel.style.backgroundColor = '#F8FCF8';
                }
            }
        });
    }
  
    // disable submit on click to prevent double submits
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Identifying...';
        }
        });
    }
  
    // ---------- PURE CLIENT-SIDE seasonal card logic (NO API calls) ----------
    (function() {
      // Sample data for each season
      const SAMPLE_SEASON_DATA = {
        "Spring": [
          { name: "Rose", scientific_name: "Rosa spp.", image: "https://picsum.photos/id/1025/600/400", medicinal_properties: "Fragrant petals used in traditional remedies.", care_tips: "Prune dead wood; apply balanced fertilizer in early spring." },
          { name: "Marigold", scientific_name: "Tagetes spp.", image: "https://picsum.photos/id/1011/600/400", medicinal_properties: "Used as antiseptic topical preparations.", care_tips: "Full sun; deadhead spent blooms; water when topsoil dries." },
          { name: "Aloe Vera", scientific_name: "Aloe barbadensis", image: "https://picsum.photos/id/1015/600/400", medicinal_properties: "Soothing gel for burns and skin.", care_tips: "Bright light; water sparingly; allow soil to dry between waterings." }
        ],
        "Summer": [
          { name: "Sunflower", scientific_name: "Helianthus annuus", image: "https://picsum.photos/id/1020/600/400", medicinal_properties: "Seeds nutritious; petals used in folk remedies.", care_tips: "Full sun; deep watering once or twice weekly." },
          { name: "Basil", scientific_name: "Ocimum basilicum", image: "https://picsum.photos/id/1021/600/400", medicinal_properties: "Used as digestive aid.", care_tips: "Full sun; pinch tips to encourage bushy growth." },
          { name: "Snake Plant", scientific_name: "Sansevieria trifasciata", image: "https://picsum.photos/id/1022/600/400", medicinal_properties: "Low-maintenance; air-purifying.", care_tips: "Low watering; bright indirect light preferred." }
        ],
        "Autumn": [
          { name: "Chrysanthemum", scientific_name: "Chrysanthemum spp.", image: "https://picsum.photos/id/1023/600/400", medicinal_properties: "Tea used for cooling effects.", care_tips: "Well-drained soil; moderate watering; deadhead for more blooms." },
          { name: "Aster", scientific_name: "Aster spp.", image: "https://picsum.photos/id/1024/600/400", medicinal_properties: "Used in folk medicine as mild diuretics.", care_tips: "Full sun to part shade; water when dry." },
          { name: "Garlic", scientific_name: "Allium sativum", image: "https://picsum.photos/id/1035/600/400", medicinal_properties: "Antimicrobial properties.", care_tips: "Plant in loose soil; mulch for winter protection." }
        ],
        "Winter": [
          { name: "Pansy", scientific_name: "Viola tricolor", image: "https://picsum.photos/id/1037/600/400", medicinal_properties: "Used in topical applications.", care_tips: "Protect from heavy frost; water lightly." },
          { name: "Rosemary", scientific_name: "Salvia rosmarinus", image: "https://picsum.photos/id/1040/600/400", medicinal_properties: "Aromatic herb used in folk remedies.", care_tips: "Full sun; reduce watering; protect from hard freezes." },
          { name: "Kale", scientific_name: "Brassica oleracea var. acephala", image: "https://picsum.photos/id/1041/600/400", medicinal_properties: "Nutrient-dense leafy green.", care_tips: "Regular watering; harvest outer leaves as needed." }
        ]
      };
  
      // Helpers: find or create seasonal container elements
      function ensureElements() {
        let seasonalContainer = document.getElementById('seasonal-plants');
        if (!seasonalContainer) {
          seasonalContainer = document.createElement('div');
          seasonalContainer.id = 'seasonal-plants';
          seasonalContainer.className = 'row g-4';
          // append after .container or to body
          const anchor = document.querySelector('.container') || document.body;
          if (anchor) anchor.appendChild(seasonalContainer);
        }
  
        // selector wrapper (top-right)
        let selectorWrapper = document.getElementById('seasonSelectorWrapper');
        if (!selectorWrapper && seasonalContainer) {
          selectorWrapper = document.createElement('div');
          selectorWrapper.id = 'seasonSelectorWrapper';
          selectorWrapper.style.display = 'flex';
          selectorWrapper.style.justifyContent = 'flex-end';
          selectorWrapper.style.marginBottom = '12px';
          seasonalContainer.appendChild(selectorWrapper);
        }
  
        // plants grid
        let plantsGrid = document.getElementById('plantsGrid');
        if (!plantsGrid && seasonalContainer) {
          plantsGrid = document.createElement('div');
          plantsGrid.id = 'plantsGrid';
          plantsGrid.className = 'd-flex flex-wrap justify-content-center';
          plantsGrid.style.gap = '1rem';
          seasonalContainer.appendChild(plantsGrid);
        }
  
        return { seasonalContainer, selectorWrapper, plantsGrid };
      }
  
      // Create plant card DOM for each plant
      function createPlantCard(plant) {
        const card = document.createElement('div');
        card.style.width = '320px';
        card.style.background = '#fff';
        card.style.borderRadius = '12px';
        card.style.boxShadow = '0 8px 20px rgba(0,0,0,0.06)';
        card.style.overflow = 'hidden';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.margin = '10px';
  
        const img = document.createElement('img');
        img.src = plant.image || '';
        img.alt = plant.name || 'plant';
        img.style.width = '100%';
        img.style.height = '200px';
        img.style.objectFit = 'cover';
        card.appendChild(img);
  
        const body = document.createElement('div');
        body.style.padding = '14px';
        body.innerHTML = `
          <h4 style="margin:0 0 6px 0; color:#155724;">${plant.name}</h4>
          <div style="font-size:0.9rem; color:#3b6b3b; font-style:italic; margin-bottom:8px;">${plant.scientific_name}</div>
          <p style="margin:0 0 10px 0; color:#666; font-size:0.95rem;">${plant.medicinal_properties}</p>
          <div style="background:#f6fffa; border-left:4px solid #4CAF50; padding:10px; border-radius:8px;">
            <strong style="display:block; color:#2e7d32; margin-bottom:6px;">🌱 Seasonal Care Tips</strong>
            <div style="color:#555; font-size:0.95rem;">${plant.care_tips}</div>
          </div>
        `;
        card.appendChild(body);
        return card;
      }
  
      // Render plants for season into #plantsGrid
      function renderSeason(season) {
        const { plantsGrid } = ensureElements();
        if (!plantsGrid) return;
        
        plantsGrid.innerHTML = '';
        const plants = SAMPLE_SEASON_DATA[season] || [];
        if (plants.length === 0) {
          plantsGrid.innerHTML = `<div style="padding:30px; color:#666;">No sample plants for ${season}</div>`;
          return;
        }
        plants.forEach(p => plantsGrid.appendChild(createPlantCard(p)));
      }
  
      // Create and wire up season dropdown (placed into #seasonSelectorWrapper)
      function setupSeasonSelector(initialSeason) {
        const { selectorWrapper } = ensureElements();
        if (!selectorWrapper) return;
        if (document.getElementById('seasonSelect')) return; // don't duplicate
  
        const label = document.createElement('label');
        label.textContent = 'Select season';
        label.style.marginRight = '10px';
        label.style.fontWeight = '600';
        label.style.color = 'var(--primary)';
        selectorWrapper.appendChild(label);
  
        const select = document.createElement('select');
        select.id = 'seasonSelect';
        select.style.padding = '10px 12px';
        select.style.borderRadius = '10px';
        select.style.border = '1px solid #e6efe6';
        select.innerHTML = `
          <option value="Spring">Spring 🌸</option>
          <option value="Summer">Summer ☀️</option>
          <option value="Autumn">Autumn 🍂</option>
          <option value="Winter">Winter ❄️</option>
        `;
        select.value = initialSeason || 'Spring';
        selectorWrapper.appendChild(select);
  
        select.addEventListener('change', function() {
          renderSeason(this.value);
        });
      }
  
      // On DOM ready: set initial season (based on month) and render sample data
      document.addEventListener('DOMContentLoaded', function() {
        const month = (new Date()).getMonth() + 1;
        const initial = month >= 3 && month <= 5 ? 'Spring' : (month >= 6 && month <= 8 ? 'Summer' : (month >= 9 && month <= 11 ? 'Autumn' : 'Winter'));
        setupSeasonSelector(initial);
        renderSeason(initial);
      });
    })();
  
    document.addEventListener('DOMContentLoaded', function() {
      // Herbal memory game data
      const herbalPairs = [
        { name: 'Basil', image: 'https://images.unsplash.com/photo-1601579537230-9a6c24d0da06?w=300&auto=format&fit=crop' },
        { name: 'Mint', image: 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=300&auto=format&fit=crop' },
        { name: 'Rosemary', image: 'https://images.unsplash.com/photo-1513531926349-466f15ec8cc7?w=300&auto=format&fit=crop' },
        { name: 'Thyme', image: 'https://images.unsplash.com/photo-1601579537230-9a6c24d0da06?w=300&auto=format&fit=crop' },
        { name: 'Oregano', image: 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=300&auto=format&fit=crop' },
        { name: 'Sage', image: 'https://images.unsplash.com/photo-1513531926349-466f15ec8cc7?w=300&auto=format&fit=crop' }
      ];
  
      const gameContainer = document.getElementById('memory-game');
      const movesCounter = document.getElementById('moves-counter');
      const resetButton = document.getElementById('reset-game');
      
      if (!gameContainer) return;
  
      let cards = [];
      let hasFlippedCard = false;
      let lockBoard = false;
      let firstCard, secondCard;
      let moves = 0;
      
      // Create cards
      function createCards() {
        // Duplicate the pairs to create matches
        const gameCards = [...herbalPairs, ...herbalPairs];
        
        // Shuffle cards
        gameCards.sort(() => Math.random() - 0.5);
        
        // Clear the game board
        gameContainer.innerHTML = '';
        
        // Create card elements
        gameCards.forEach((card, index) => {
          const cardElement = document.createElement('div');
          cardElement.classList.add('memory-card');
          cardElement.dataset.name = card.name;
          cardElement.dataset.index = index;
          
          cardElement.innerHTML = `
            <div class="memory-card-inner">
              <div class="memory-card-front">
                <span>?</span>
              </div>
              <div class="memory-card-back">
                <img src="${card.image}" alt="${card.name}">
                <div style="position: absolute; bottom: 10px; left: 0; right: 0; text-align: center; background: rgba(255,255,255,0.8); padding: 5px; font-weight: bold; color: #1A5D1A;">${card.name}</div>
              </div>
            </div>
          `;
          
          cardElement.addEventListener('click', flipCard);
          gameContainer.appendChild(cardElement);
          cards.push(cardElement);
        });
      }
      
      // Flip card function
      function flipCard() {
        if (lockBoard) return;
        if (this === firstCard) return;
        if (this.classList.contains('matched')) return;
        
        this.classList.add('flipped');
        
        if (!hasFlippedCard) {
          // First click
          hasFlippedCard = true;
          firstCard = this;
          return;
        }
        
        // Second click
        secondCard = this;
        checkForMatch();
        updateMoves();
      }
      
      // Check for a match
      function checkForMatch() {
        const isMatch = firstCard.dataset.name === secondCard.dataset.name;
        
        if (isMatch) {
          disableCards();
        } else {
          unflipCards();
        }
      }
      
      // Disable matched cards
      function disableCards() {
        firstCard.classList.add('matched');
        secondCard.classList.add('matched');
        
        resetBoard();
        
        // Check if game is won
        if (document.querySelectorAll('.matched').length === cards.length) {
          setTimeout(() => {
            alert(`Congratulations! You won in ${moves} moves!`);
          }, 500);
        }
      }
      
      // Unflip cards if no match
      function unflipCards() {
        lockBoard = true;
        
        setTimeout(() => {
          firstCard.classList.remove('flipped');
          secondCard.classList.remove('flipped');
          
          resetBoard();
        }, 1000);
      }
      
      // Reset board state
      function resetBoard() {
        [hasFlippedCard, lockBoard] = [false, false];
        [firstCard, secondCard] = [null, null];
      }
      
      function updateMoves() {
        moves++;
        if (movesCounter) movesCounter.querySelector('span').textContent = moves;
      }
      
      if (resetButton) {
        resetButton.addEventListener('click', () => {
            moves = 0;
            if (movesCounter) movesCounter.querySelector('span').textContent = moves;
            createCards();
        });
      }
      
      // Initialize game
      createCards();
    });
