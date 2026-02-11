// Gallery carousel - loads video config from JSON

// Utility functions
function formatVideoName(filename, phases = 2) {
    let name = filename.replace('.mp4', '').replace(/^\(\d+\)/, '');
    const parts = name.split('+');
    
    if (parts.length >= phases) {
        const formatted = parts.map(part => {
            const cleanPart = part.replace(/-\d+$/, '').replace(/_/g, ' ');
            return cleanPart.charAt(0).toUpperCase() + cleanPart.slice(1);
        });
        return formatted.join(' → ');
    }
    return name;
}

function formatThumbnailName(filename, phases = 2) {
    let name = filename.replace('.mp4', '').replace(/^\(\d+\)/, '');
    const parts = name.split('+');
    
    if (parts.length >= phases) {
        return parts.map(part => part.replace(/-\d+$/, '')).join(' → ');
    }
    return name;
}

// Video carousel controller for gallery pages
class GalleryCarousel {
    constructor(category, phases = 2, configPath = '../static/js/gallery-config.json') {
        this.category = category;
        this.phases = phases;
        this.configPath = configPath;
        this.currentIndex = 0;
        this.isAnimating = false;
        
        this.videoElement = document.getElementById('galleryVideo');
        this.videoWrapper = this.videoElement.parentElement;
        this.videoTitle = document.getElementById('galleryVideoTitle');
        this.currentNum = document.getElementById('galleryCurrentNum');
        this.totalNum = document.getElementById('galleryTotalNum');
        this.progressFill = document.getElementById('galleryProgressFill');
        this.thumbnailStrip = document.getElementById('galleryThumbnailStrip');
        this.prevBtn = document.getElementById('galleryPrevBtn');
        this.nextBtn = document.getElementById('galleryNextBtn');
        
        this.loadConfig();
    }
    
    async loadConfig() {
        try {
            const response = await fetch(this.configPath);
            const config = await response.json();
            
            if (config[this.category]) {
                this.videos = config[this.category].videos;
                this.basePath = config[this.category].basePath;
                this.init();
            } else {
                console.error(`Category "${this.category}" not found in config`);
                this.videoTitle.textContent = 'Error: Category not found';
            }
        } catch (error) {
            console.error('Failed to load gallery config:', error);
            this.videoTitle.textContent = 'Error loading videos';
        }
    }
    
    init() {
        // Ensure playsInline is set for mobile devices (especially iOS)
        this.videoElement.setAttribute('playsinline', '');
        this.videoElement.playsInline = true;
        
        this.totalNum.textContent = this.videos.length;
        this.createThumbnails();
        this.setupEventListeners();
        this.updateCarousel();
        
        this.videoElement.addEventListener('loadedmetadata', () => {
            if (!this.videoWrapper.style.minHeight) {
                this.videoWrapper.style.minHeight = this.videoWrapper.offsetHeight + 'px';
            }
        }, { once: true });
    }
    
    createThumbnails() {
        this.thumbnailStrip.innerHTML = '';
        this.videos.forEach((video, index) => {
            const item = document.createElement('div');
            item.className = 'gallery-thumbnail-item' + (index === 0 ? ' active' : '');
            item.textContent = formatThumbnailName(video, this.phases);
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToVideo(index);
            });
            this.thumbnailStrip.appendChild(item);
        });
    }
    
    setupEventListeners() {
        this.prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.prevVideo();
        });
        
        this.nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.nextVideo();
        });
        
        this.videoElement.addEventListener('ended', () => {
            if (this.currentIndex < this.videos.length - 1) {
                this.nextVideo();
            } else {
                this.currentIndex = 0;
                this.updateCarousel('next');
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.prevVideo();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.nextVideo();
            }
        });
    }
    
    updateCarousel(direction = 'none') {
        if (this.isAnimating && direction !== 'none') return;
        
        const video = this.videos[this.currentIndex];
        const savedScrollY = window.scrollY;
        const savedScrollX = window.scrollX;
        
        const currentHeight = this.videoWrapper.offsetHeight;
        this.videoWrapper.style.height = currentHeight + 'px';
        
        if (direction !== 'none') {
            this.isAnimating = true;
            const slideOut = direction === 'next' ? 'slide-out-left' : 'slide-out-right';
            const slideIn = direction === 'next' ? 'slide-in-right' : 'slide-in-left';
            
            this.videoElement.classList.add(slideOut);
            
            setTimeout(() => {
                this.videoElement.src = this.basePath + encodeURIComponent(video);
                this.videoElement.load();
                window.scrollTo(savedScrollX, savedScrollY);
                
                this.videoElement.classList.remove(slideOut);
                this.videoElement.classList.add(slideIn);
                this.videoElement.offsetHeight;
                
                requestAnimationFrame(() => {
                    this.videoElement.classList.remove(slideIn);
                    this.videoElement.play();
                    window.scrollTo(savedScrollX, savedScrollY);
                    
                    setTimeout(() => {
                        this.isAnimating = false;
                    }, 500);
                    
                    this.videoElement.addEventListener('loadedmetadata', () => {
                        this.videoWrapper.style.height = '';
                        window.scrollTo(savedScrollX, savedScrollY);
                    }, { once: true });
                });
            }, 500);
        } else {
            this.videoElement.src = this.basePath + encodeURIComponent(video);
            this.videoElement.load();
            this.videoElement.play();
            
            this.videoElement.addEventListener('loadedmetadata', () => {
                this.videoWrapper.style.height = '';
            }, { once: true });
        }
        
        this.videoTitle.textContent = formatVideoName(video, this.phases);
        this.currentNum.textContent = this.currentIndex + 1;
        this.progressFill.style.width = ((this.currentIndex + 1) / this.videos.length * 100) + '%';
        
        const thumbnails = this.thumbnailStrip.querySelectorAll('.gallery-thumbnail-item');
        thumbnails.forEach((item, index) => {
            item.classList.toggle('active', index === this.currentIndex);
        });
        
        window.scrollTo(savedScrollX, savedScrollY);
        
        this.prevBtn.disabled = this.currentIndex === 0;
        this.nextBtn.disabled = this.currentIndex === this.videos.length - 1;
    }
    
    goToVideo(index) {
        const oldIndex = this.currentIndex;
        this.currentIndex = Math.max(0, Math.min(index, this.videos.length - 1));
        if (oldIndex !== this.currentIndex) {
            this.updateCarousel(index > oldIndex ? 'next' : 'prev');
        }
    }
    
    nextVideo() {
        if (this.currentIndex < this.videos.length - 1 && !this.isAnimating) {
            this.currentIndex++;
            this.updateCarousel('next');
        }
    }
    
    prevVideo() {
        if (this.currentIndex > 0 && !this.isAnimating) {
            this.currentIndex--;
            this.updateCarousel('prev');
        }
    }
}
