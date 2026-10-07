"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TripDetail } from "@/lib/types";

export const tripKeys = {
  all: ["trips"] as const,
  detail: (id: string) => ["trips", id] as const,
};

export function useTrips() {
  return useQuery({ queryKey: tripKeys.all, queryFn: api.listTrips });
}

export function useTrip(id: string) {
  return useQuery({ queryKey: tripKeys.detail(id), queryFn: () => api.getTrip(id) });
}

export function useCreateTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createTrip,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tripKeys.all }),
  });
}

export function useDeleteTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteTrip,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tripKeys.all }),
  });
}

/** Swap the plan's hotel. No AI involved, so the board updates straight away. */
export function useChooseHotel(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (hotel: string) => api.chooseHotel(tripId, hotel),
    onSuccess: (update) => {
      queryClient.setQueryData<TripDetail>(tripKeys.detail(tripId), (old) =>
        old ? { ...old, trip: { ...old.trip, ...update } } : old,
      );
    },
  });
}
