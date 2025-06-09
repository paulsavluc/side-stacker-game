import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store/store';
import GameMenu from './components/GameMenu';
import GameBoard from './components/GameBoard';
import './App.scss';

function App() {
  return (
    <Provider store={store}>
      <Router>
        <div className="App">
          <h1>Side-Stacker Game</h1>
          <Routes>
            <Route path="/" element={<GameMenu />} />
            <Route path="/game/:gameId" element={<GameBoard />} />
          </Routes>
        </div>
      </Router>
    </Provider>
  );
}

export default App;
