import React from 'react';
import '../../styles/About.css';


/**
 * About Tab for Conure ProjectView
 */
function About() {
  return (
    <div className="about-container">
      <header className="about-header">
        <h2>Conure</h2>
        <p>Your RF inductor design companion</p>
        <h5>Version: 0.2.0</h5>
        
      </header>

      <div className="about-content">
        <section className="about-description">
          <p>
            <strong>Conure</strong> is a versatile toolkit that unifies design, simulation, and modeling within a single, intuitive interface.
          </p>
        </section>

        <section className="about-details">
          <div className="about-section">
            <h3>Getting Started</h3>
            <p>
              See the{' '}
              <a href="../README.md" target="_blank" rel="noopener noreferrer">
                README
              </a>{' '}
              for installation, quickstart commands, and full documentation.
            </p>
          </div>

          <div className="about-section">
            <h3>Contributors</h3>
            <ul className="contributor-list">
              <li>Habibur Rahman</li>
              <li>Adrian Llop Recha</li>
              <li>Stefano Fasciani</li>
              <li>Pål Gunnar Hogganvik</li>
              <li>Kristian Kjelgård</li>
              <li>Dag Wisland</li>
            </ul>
          </div>
        </section>
      </div>

      <footer className="about-footer">
        <div className="logo-wrapper">
          <a href="https://github.com/emoninet2/Conure" target="_blank" rel="noopener noreferrer">
            <img
              src="/githubLinkQRCode.jpg"
              alt="GitHub Repository QR Code"
              className="footer-logo"
            />
          </a>
        </div>
        <div className="logo-wrapper">
          <a href="https://uio.no" target="_blank" rel="noopener noreferrer">
            <img
              src="/03_uio_full_logo_eng_pos.png"
              alt="University of Oslo Logo"
              className="footer-logo"
            />
          </a>
        </div>
        <div className="logo-wrapper">
          <a href="https://emon.no/" target="_blank" rel="noopener noreferrer">
            <img
              src="/emon_no_logo.webp"
              alt="emon_no_logo"
              className="footer-logo"
            />
          </a>
        </div>
      </footer>
    </div>
  );
}

export default About;
