class TeaTimer {
    constructor() {
    this.duration = 0;
    this.elapsed = 0;
    this.isActive = false;
    this.lastFrameTime = Date.now();
    this.onTick = () => {};
    this.onCompleted = () => {};
    this.tick();
  }

  getTimeLeft() {
    const t = this.duration - this.elapsed;
    return Math.max(0, t);
  }

  pause() {
    this.isActive = false;
    return this;
  }
  reset(d) {
    this.elapsed = 0;
    this.setDuration(d);
  }
  setDuration(seconds) {
    this.lastFrameTime = Date.now();
    this.duration = seconds;
    return this;
  }

  start(d) {
    this.elapsed = 0;
    this.setDuration(d);
    this.isActive = true;
    return this;
  }

  tick() {
    const currentFrameTime = Date.now();
    const deltaTime = currentFrameTime - this.lastFrameTime;
    this.lastFrameTime = currentFrameTime;

    if (this.isActive) {
      this.elapsed += deltaTime / 1000;
      this.onTick(this.getTimeLeft());

      if(this.getTimeLeft() <= 0) {
        this.pause();
        this.onCompleted();
      }
    }

    window.requestAnimationFrame(this.tick.bind(this));
  }
};

function format_timer(secs) {
    m = Math.floor(secs / 60);
    s = secs % 60;
    if (m < 10) {
      m =  "0" + m;
    if (s < 10) {
      s = "0" + s;
    }
    return m + ":" + s;
  }
}