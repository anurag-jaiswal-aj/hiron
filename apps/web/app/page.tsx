"use client";
import React from "react";
import { ProductNarrative } from "../components/landing/ProductNarrative";
import { Navbar } from "../components/landing/Navbar";

export default function LandingPage(): React.ReactElement {
  return (
    <>
      <Navbar />
      <ProductNarrative />
    </>
  );
}
