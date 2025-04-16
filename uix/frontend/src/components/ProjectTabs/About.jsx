import React from 'react';

/**
 * About Tab for Conure ProjectView
 */
function About() {
  // Styles for container and elements
  const containerStyle = {
    backgroundColor: '#ffffff',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    maxWidth: '800px',
    margin: '2rem auto',
    color: '#333333',
    lineHeight: '1.6',
  };
  const titleStyle = {
    textAlign: 'center',
    fontSize: '2.5rem',
    marginBottom: '1rem',
    color: '#007bff',
  };
  const sectionTitleStyle = {
    fontSize: '1.5rem',
    marginTop: '1.5rem',
    marginBottom: '0.5rem',
    color: '#0056b3',
  };
  const linkStyle = {
    color: '#007bff',
    textDecoration: 'none',
  };
  const listStyle = {
    listStyleType: 'none',
    paddingLeft: 0,
    marginLeft: 0,
    lineHeight: '1.8',
  };

  return (
    <div style={containerStyle}>
      <h2 style={titleStyle}>About Conure</h2>
      <p>
        Conure is a comprehensive toolkit for designing, simulating, modeling, and optimizing RFCMOS integrated inductors.
      </p>

      <h3 style={sectionTitleStyle}>Getting Started</h3>
      <p>
        Refer to the{' '}
        <a href="../README.md" target="_blank" rel="noopener noreferrer" style={linkStyle}>
          README
        </a>{' '}
        for installation instructions, quick-start examples, and detailed documentation.
      </p>

      <h3 style={sectionTitleStyle}>Contributors</h3>
      <ul style={listStyle}>
        <li>Habibur Rahman</li>
        <li>Adrian Llop Recha</li>
        <li>Stefano Fasciani</li>
        <li>Pål Gunnar Hogganvik</li>
        <li>Kristian Kjelgård</li>
        <li>Dag Wisland</li>
      </ul>
    </div>
  );
}

export default About;
